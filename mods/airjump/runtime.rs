use std::fs;
use std::path::Path;
use std::sync::Mutex;

use horizon_client::items::ItemStack;
use horizon_client::keybinds::{key_code, mouse_button};
use horizon_client::motion::MotionWorld;
use horizon_client::particles::{ParticleOptions, ParticleType};
use horizon_core::random::RandomSource;
use horizon_world::view_direction::view_vector;
use serde::{Deserialize, Serialize};
use winit::event::MouseButton;

use crate::game::{Game, Screen};

const DEFAULT_LAUNCH_WAND: &str = "minecraft:stick";
const DEFAULT_LAUNCH_VELOCITY: f64 = 5.0;

fn yes() -> bool {
    true
}

fn default_wand() -> String {
    DEFAULT_LAUNCH_WAND.to_owned()
}

fn default_velocity() -> f64 {
    DEFAULT_LAUNCH_VELOCITY
}

fn sanitize_velocity(value: f64) -> f64 {
    if !value.is_finite() || value <= 0.0 {
        DEFAULT_LAUNCH_VELOCITY
    } else {
        value.clamp(0.1, 20.0)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
struct Config {
    #[serde(default = "yes")]
    multi_jump: bool,
    #[serde(default = "yes")]
    launch: bool,
    #[serde(default = "yes")]
    no_fall_damage: bool,
    #[serde(default = "default_wand", rename = "launchWand")]
    launch_wand: String,
    #[serde(default = "default_velocity", rename = "launchVelocity")]
    launch_velocity: f64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            multi_jump: true,
            launch: true,
            no_fall_damage: true,
            launch_wand: default_wand(),
            launch_velocity: default_velocity(),
        }
    }
}

impl Config {
    fn load() -> Self {
        let Ok(dir) = Game::native_config_dir() else {
            return Self::default();
        };
        let path = dir.join("airjump.json");
        let mut config = match fs::read_to_string(&path) {
            Ok(text) => match serde_json::from_str::<Self>(&text) {
                Ok(config) => config,
                Err(_) => {
                    let config = Self::default();
                    config.save(&path);
                    config
                }
            },
            Err(_) => {
                let config = Self::default();
                config.save(&path);
                config
            }
        };
        config.sanitize();
        config
    }

    fn sanitize(&mut self) {
        self.launch_wand = self.launch_wand.trim().to_owned();
        if self.launch_wand.is_empty() {
            self.launch_wand = default_wand();
        }
        self.launch_velocity = sanitize_velocity(self.launch_velocity);
    }

    fn save(&self, path: &Path) {
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(text) = serde_json::to_string_pretty(self) {
            let _ = fs::write(path, text);
        }
    }
}

struct State {
    config: Config,
    was_jumping: bool,
    was_right_clicking: bool,
    launch_ticks: i32,
}

impl State {
    fn load() -> Self {
        Self {
            config: Config::load(),
            was_jumping: false,
            was_right_clicking: false,
            launch_ticks: 0,
        }
    }
}

static STATE: Mutex<Option<State>> = Mutex::new(None);

fn key_down(game: &mut Game<'_>, name: &str) -> bool {
    let assigned = game.settings.keys.get(name).to_owned();
    if let Some(code) = key_code(&assigned) {
        return game.keys.raw(&code);
    }
    let Some(button) = mouse_button(&assigned) else {
        return false;
    };
    let held = game.mouse_reading().1;
    match button {
        MouseButton::Left => held[0],
        MouseButton::Right => held[1],
        _ => false,
    }
}

fn crosshair_miss(game: &Game<'_>) -> bool {
    game.pick().is_none() && game.mob_hit_within(game.entity_reach).is_none()
}

fn main_hand_is(game: &Game<'_>, item: &str) -> bool {
    game.inventory
        .get(game.selected)
        .and_then(|stack| stack.as_ref())
        .is_some_and(|stack| &*stack.item == item)
}

fn holds(game: &Game<'_>, item: &str) -> bool {
    main_hand_is(game, item) || game.offhand.as_ref().is_some_and(|stack| &*stack.item == item)
}

fn send_no_fall(game: &mut Game<'_>, horizontal_collision: bool) {
    let flags = 1 | (u8::from(horizontal_collision) << 1);
    let packet = horizon_protocol::packets::play::Serverbound::MovePlayerStatus(
        horizon_protocol::packets::play::MovePlayerStatus { flags },
    );
    let _ = game.native_send_packet(packet);
}

fn explosion(game: &mut Game<'_>, at: [f64; 3]) {
    let velocity = {
        let random = game.particles.random();
        [
            (random.next_double() - 0.5) * 0.4,
            random.next_double() * 0.2,
            (random.next_double() - 0.5) * 0.4,
        ]
    };
    game.particles.add(
        &ParticleOptions::simple(ParticleType::Explosion),
        [at[0], at[1] + 0.4, at[2]],
        velocity,
    );
}

pub fn tick(game: &mut Game<'_>) {
    if game.player.is_none() {
        return;
    }

    let mut guard = STATE.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    let state = guard.get_or_insert_with(State::load);

    let jumping = key_down(game, "key.jump");
    let sneaking = key_down(game, "key.sneak");
    let right_clicking = key_down(game, "key.use");
    let air_use = right_clicking
        && game.using.is_none()
        && game.screen == Screen::Playing
        && crosshair_miss(game);

    if state.launch_ticks <= 8 {
        state.launch_ticks += 1;
        if let Some(player) = game.player.as_ref() {
            explosion(
                game,
                [player.position.x, player.position.y, player.position.z],
            );
        }
    }

    if state.config.multi_jump {
        if jumping && !state.was_jumping {
            if let Some(player) = game.player.as_mut() {
                let mut world = MotionWorld {
                    entities: &[],
                    player,
                    scene: &mut game.world,
                    assets: &game.pack.assets,
                    collision_binding: game.collision,
                    resources: game.motion,
                    health: &game.health_resources,
                };
                let _ = world.jump_from_ground();
            }
        }
        if sneaking
            && let Some(player) = game.player.as_mut()
            && player.fall_distance > 0.0
        {
            player.velocity.y = 0.0;
        }
    }

    let configured_wand = state.config.launch_wand.clone();
    let wand = if game.items().items.contains_key(configured_wand.as_str()) {
        configured_wand.as_str()
    } else {
        DEFAULT_LAUNCH_WAND
    };

    if state.config.launch && air_use && !state.was_right_clicking && holds(game, wand) {
        if sneaking {
            game.native_chat("-- SuperLaunch isn't allowed during sneak!");
            state.was_jumping = jumping;
            state.was_right_clicking = true;
            return;
        }
        if let Some(player) = game.player.as_mut() {
            let dir = view_vector(player.pitch, player.yaw);
            let mut boosted = dir.scale(state.config.launch_velocity);
            if boosted.y < 0.0 {
                boosted.y = player.velocity.y;
            }
            player.velocity = boosted;
        }
        if let Some(player) = game.player.as_ref() {
            let _ = game.native_play_local_sound(
                "minecraft:entity.generic.explode",
                [player.position.x, player.position.y, player.position.z],
                0.9,
                1.2,
                0,
            );
        }
        state.launch_ticks = 0;
    }

    if state.config.no_fall_damage
        && !game.creative
        && !main_hand_is(game, "minecraft:mace")
        && !game.armor[1]
            .as_ref()
            .is_some_and(|stack| &*stack.item == "minecraft:elytra")
    {
        if let Some(player) = game.player.as_ref()
            && player.fall_distance > 2.5
        {
            send_no_fall(game, player.collision.horizontal);
        }
    }

    state.was_jumping = jumping;
    state.was_right_clicking = air_use;
}
