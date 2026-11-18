"""Rust runtime embedded in every generated blockforge program.

It uses SDL2 through a tiny set of direct FFI declarations.  That keeps the
generated file buildable with plain ``rustc`` and avoids requiring Cargo,
crates, or network access on the machine that runs the program.
"""

SOURCE = r'''
// --- blockforge runtime ----------------------------------------------------
use std::cell::Cell;
use std::collections::HashMap;
use std::ffi::{c_char, c_void, CString};
use std::ptr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::Duration;

thread_local! {
    static BF_STOPPING: Cell<bool> = Cell::new(false);
}

// Scratch-style "stop this script" is thread-local so it also propagates out
// of a called custom block without ending the whole program.
fn bf_reset_script() { BF_STOPPING.with(|value| value.set(false)); }
fn bf_should_stop() -> bool { BF_STOPPING.with(|value| value.get()) }
fn bf_stop_script() { BF_STOPPING.with(|value| value.set(true)); }

const BF_PI: f64 = std::f64::consts::PI;
const SDL_INIT_AUDIO: u32 = 0x00000010;
const SDL_INIT_VIDEO: u32 = 0x00000020;
const SDL_WINDOW_SHOWN: u32 = 0x00000004;
const SDL_WINDOWPOS_CENTERED: i32 = 0x2fff0000;
const SDL_RENDERER_SOFTWARE: u32 = 0x00000001;
const SDL_RENDERER_ACCELERATED: u32 = 0x00000002;
const SDL_QUIT: u32 = 0x00000100;
const AUDIO_S16SYS: u16 = 0x8010;

#[repr(C)]
struct BfRect { x: i32, y: i32, w: i32, h: i32 }

#[repr(C, align(8))]
struct BfEvent { bytes: [u8; 128] }

#[repr(C)]
struct BfAudioSpec {
    freq: i32,
    format: u16,
    channels: u8,
    silence: u8,
    samples: u16,
    size: u32,
    callback: Option<unsafe extern "C" fn(*mut c_void, *mut u8, i32)>,
    userdata: *mut c_void,
}

extern "C" {
    fn SDL_Init(flags: u32) -> i32;
    fn SDL_Quit();
    fn SDL_CreateWindow(title: *const c_char, x: i32, y: i32, w: i32, h: i32,
                        flags: u32) -> *mut c_void;
    fn SDL_DestroyWindow(window: *mut c_void);
    fn SDL_CreateRenderer(window: *mut c_void, index: i32, flags: u32) -> *mut c_void;
    fn SDL_DestroyRenderer(renderer: *mut c_void);
    fn SDL_SetRenderDrawColor(renderer: *mut c_void, r: u8, g: u8, b: u8, a: u8) -> i32;
    fn SDL_RenderClear(renderer: *mut c_void) -> i32;
    fn SDL_RenderFillRect(renderer: *mut c_void, rect: *const BfRect) -> i32;
    fn SDL_RenderDrawRect(renderer: *mut c_void, rect: *const BfRect) -> i32;
    fn SDL_RenderDrawLine(renderer: *mut c_void, x1: i32, y1: i32, x2: i32, y2: i32) -> i32;
    fn SDL_RenderPresent(renderer: *mut c_void);
    fn SDL_Delay(ms: u32);
    fn SDL_GetTicks() -> u32;
    fn SDL_GetKeyboardState(count: *mut i32) -> *const u8;
    fn SDL_GetMouseState(x: *mut i32, y: *mut i32) -> u32;
    fn SDL_PollEvent(event: *mut c_void) -> i32;
    fn SDL_OpenAudioDevice(device: *const c_char, capture: i32,
                           desired: *const BfAudioSpec, obtained: *mut BfAudioSpec,
                           allowed: i32) -> u32;
    fn SDL_PauseAudioDevice(device: u32, pause: i32);
    fn SDL_CloseAudioDevice(device: u32);
}

#[derive(Clone)]
struct Value {
    kind: u8, // 0 number, 1 text, 2 boolean
    number: f64,
    text: String,
    boolean: bool,
}

impl Value {
    fn num(number: f64) -> Value {
        Value { kind: 0, number, text: String::new(), boolean: false }
    }
    fn text(text: String) -> Value {
        Value { kind: 1, number: 0.0, text, boolean: false }
    }
    fn boolean(boolean: bool) -> Value {
        Value { kind: 2, number: if boolean { 1.0 } else { 0.0 },
                text: String::new(), boolean }
    }
    fn as_num(&self) -> f64 {
        match self.kind {
            1 => self.text.trim().parse::<f64>().unwrap_or(0.0),
            2 => if self.boolean { 1.0 } else { 0.0 },
            _ => self.number,
        }
    }
    fn as_text(&self) -> String {
        match self.kind {
            1 => self.text.clone(),
            2 => if self.boolean { "true".to_string() } else { "false".to_string() },
            _ => {
                let value = self.number;
                if value.is_nan() { return "nan".to_string(); }
                if value == 0.0 { return "0".to_string(); }
                let rounded = value.round();
                if value.is_finite() &&
                   (value - rounded).abs() <= 1e-12 * value.abs().max(1.0) {
                    format!("{}", rounded as i64)
                } else {
                    format!("{}", value)
                }
            },
        }
    }
    fn as_bool(&self) -> bool {
        match self.kind {
            1 => !self.text.is_empty(),
            2 => self.boolean,
            _ => self.number != 0.0,
        }
    }
}

impl From<f64> for Value {
    fn from(value: f64) -> Value { Value::num(value) }
}
impl From<i32> for Value {
    fn from(value: i32) -> Value { Value::num(value as f64) }
}
impl From<usize> for Value {
    fn from(value: usize) -> Value { Value::num(value as f64) }
}
impl From<bool> for Value {
    fn from(value: bool) -> Value { Value::boolean(value) }
}
impl From<String> for Value {
    fn from(value: String) -> Value { Value::text(value) }
}
impl From<&str> for Value {
    fn from(value: &str) -> Value { Value::text(value.to_string()) }
}

fn bf_ticks() -> u32 {
    unsafe { SDL_GetTicks() }
}

fn bf_color(value: &str) -> (u8, u8, u8) {
    if value.len() >= 7 && value.starts_with('#') {
        let parse = |from: usize, to: usize| {
            u8::from_str_radix(&value[from..to], 16).unwrap_or(124)
        };
        (parse(1, 3), parse(3, 5), parse(5, 7))
    } else {
        (124, 108, 255)
    }
}

fn bf_visual_radius(size: f64) -> f64 {
    (size / 100.0 * 36.0).max(4.0) / 2.0
}

fn bf_print_text(text: &str) {
    let mut normalized = text.to_string();
    if normalized.ends_with('\n') {
        normalized.pop();
        if normalized.ends_with('\r') { normalized.pop(); }
    }
    if normalized.is_empty() {
        println!();
        return;
    }
    for line in normalized.split('\n') {
        println!("{}", line.trim_end_matches('\r'));
    }
}

fn bf_draw_star(renderer: *mut c_void, cx: i32, cy: i32, size: i32) {
    let point_count = 10usize;
    let outer = size as f64 / 2.0;
    let mut points = [(0i32, 0i32); 10];
    for index in 0..point_count {
        let factor = if index % 2 == 0 { 1.0 } else { 0.45 };
        let angle = (-90.0 + index as f64 * 36.0) * BF_PI / 180.0;
        points[index] = (
            cx + (angle.cos() * outer * factor).round() as i32,
            cy + (angle.sin() * outer * factor).round() as i32,
        );
    }
    let lowest = points.iter().map(|point| point.1).min().unwrap();
    let highest = points.iter().map(|point| point.1).max().unwrap();
    for y in lowest..=highest {
        let mut crossings: Vec<f64> = Vec::new();
        for index in 0..point_count {
            let (x1, y1) = points[index];
            let (x2, y2) = points[(index + 1) % point_count];
            if (y1 <= y && y2 > y) || (y2 <= y && y1 > y) {
                crossings.push(x1 as f64 + (y - y1) as f64
                    * (x2 - x1) as f64 / (y2 - y1) as f64);
            }
        }
        crossings.sort_by(|left, right| left.partial_cmp(right).unwrap());
        let mut index = 0;
        while index + 1 < crossings.len() {
            unsafe {
                SDL_RenderDrawLine(renderer, crossings[index].ceil() as i32,
                    y, crossings[index + 1].floor() as i32, y);
            }
            index += 2;
        }
    }
    for index in 0..point_count {
        let (x1, y1) = points[index];
        let (x2, y2) = points[(index + 1) % point_count];
        unsafe { SDL_RenderDrawLine(renderer, x1, y1, x2, y2); }
    }
}

struct BfLine {
    x1: f64, y1: f64, x2: f64, y2: f64,
    color: (u8, u8, u8), size: i32,
}

#[derive(Clone)]
struct BfSprite {
    name: String,
    x: f64, y: f64, size: f64, direction: f64,
    visible: bool,
    costume: usize, costume_count: usize, layer: i32,
    shape: String,
    color: String,
    say_until: u32,
    say_text: String,
}

impl BfSprite {
    fn new(name: &str) -> BfSprite {
        BfSprite {
            name: name.to_string(), x: 0.0, y: 0.0, size: 100.0,
            direction: 90.0, visible: true, costume: 1, costume_count: 2,
            layer: 0, shape: "circle".to_string(), color: "#4c9ffe".to_string(),
            say_until: 0, say_text: String::new(),
        }
    }
}

struct AudioState { freq: f64, left: f64, phase: f64 }
static AUDIO: OnceLock<Mutex<AudioState>> = OnceLock::new();

unsafe extern "C" fn bf_audio_callback(_user: *mut c_void, stream: *mut u8, length: i32) {
    let state = AUDIO.get_or_init(|| Mutex::new(AudioState { freq: 0.0, left: 0.0, phase: 0.0 }));
    let mut audio = state.lock().unwrap();
    let count = (length as usize) / 2;
    for index in 0..count {
        let sample = if audio.freq > 0.0 && audio.left > 0.0 {
            let wave = (2.0 * BF_PI * audio.phase * audio.freq).sin();
            audio.phase += 1.0 / 44100.0;
            (wave * 12000.0) as i16
        } else { 0i16 };
        std::ptr::write_unaligned(stream.add(index * 2) as *mut i16, sample);
    }
    audio.left = (audio.left - length as f64 / (44100.0 * 2.0)).max(0.0);
}

struct App {
    width: i32,
    height: i32,
    background: String,
    sprites: Vec<BfSprite>,
    vars: HashMap<String, Value>,
    lines: Vec<BfLine>,
    keys: [bool; 256],
    pointer_x: f64,
    pointer_y: f64,
    started: u32,
    rng_state: u64,
    audio_device: u32,
    pen_active: bool,
    pen_color: (u8, u8, u8),
    pen_size: i32,
    running: Arc<AtomicBool>,
}

impl App {
    fn new(width: i32, height: i32, background: &str) -> App {
        let tick = bf_ticks();
        App {
            width, height, background: background.to_string(),
            sprites: Vec::new(), vars: HashMap::new(), lines: Vec::new(),
            keys: [false; 256], pointer_x: 0.0, pointer_y: 0.0,
            started: tick, rng_state: ((tick as u64) << 16) | 0x2545f491,
            audio_device: 0, pen_active: false, pen_color: (74, 222, 128),
            pen_size: 3, running: Arc::new(AtomicBool::new(true)),
        }
    }
    fn sprite(&mut self, index: usize) -> &mut BfSprite {
        if self.sprites.is_empty() {
            self.sprites.push(BfSprite::new("Sprite"));
        }
        let slot = index % self.sprites.len();
        &mut self.sprites[slot]
    }
    fn num(&self, value: Value) -> f64 { value.as_num() }
    fn text(&self, value: Value) -> String { value.as_text() }
    fn as_bool(&self, value: Value) -> bool { value.as_bool() }
    fn join(&self, left: Value, right: Value) -> String {
        left.as_text() + &right.as_text()
    }
    fn equal(&self, left: Value, right: Value) -> bool {
        if left.kind == 1 && right.kind == 1 {
            left.text == right.text
        } else {
            left.as_num() == right.as_num()
        }
    }
    fn not_equal(&self, left: Value, right: Value) -> bool {
        !self.equal(left, right)
    }
    fn length(&self, value: Value) -> f64 {
        value.as_text().chars().count() as f64
    }
    fn abs_num(&self, value: f64) -> f64 { value.abs() }
    fn sqrt_num(&self, value: f64) -> f64 { value.max(0.0).sqrt() }
    fn sin_num(&self, value: f64) -> f64 { value.sin() }
    fn cos_num(&self, value: f64) -> f64 { value.cos() }
    fn round_num(&self, value: f64) -> f64 { value.round() }
    fn floor_num(&self, value: f64) -> f64 { value.floor() }
    fn ceil_num(&self, value: f64) -> f64 { value.ceil() }
    fn print_line(&self, value: Value) {
        bf_print_text(&value.as_text());
    }
    fn timer(&self) -> f64 { (bf_ticks() - self.started) as f64 / 1000.0 }
    fn mouse_x(&self) -> f64 { self.pointer_x }
    fn mouse_y(&self) -> f64 { self.pointer_y }

    fn touching_edge(&mut self, index: usize) -> bool {
        let (x, y, half) = {
            let item = self.sprite(index);
            (item.x, item.y, bf_visual_radius(item.size))
        };
        let right = self.width as f64 / 2.0;
        let top = self.height as f64 / 2.0;
        (x.abs() + half >= right) || (y.abs() + half >= top)
    }
    fn touching_sprite(&mut self, first: usize, second: usize) -> bool {
        let (a_x, a_y, a_size) = {
            let a = self.sprite(first);
            (a.x, a.y, a.size)
        };
        let (b_x, b_y, b_size) = {
            let b = self.sprite(second);
            (b.x, b.y, b.size)
        };
        let dx = a_x - b_x;
        let dy = a_y - b_y;
        (dx * dx + dy * dy).sqrt() < (a_size + b_size) / 4.0
    }
    fn move_sprite(&mut self, index: usize, steps: f64) {
        let (direction, x, y) = {
            let item = self.sprite(index);
            (item.direction, item.x, item.y)
        };
        let radians = direction * BF_PI / 180.0;
        let nx = x + radians.sin() * steps;
        let ny = y + radians.cos() * steps;
        if self.pen_active {
            let color = self.pen_color;
            let size = self.pen_size;
            self.lines.push(BfLine {
                x1: x, y1: y, x2: nx, y2: ny, color, size,
            });
            if self.lines.len() > 5000 { self.lines.remove(0); }
        }
        let item = self.sprite(index);
        item.x = nx;
        item.y = ny;
    }
    fn turn(&mut self, index: usize, degrees: f64) {
        let item = self.sprite(index);
        item.direction = (item.direction + degrees).rem_euclid(360.0);
    }
    fn set_direction(&mut self, index: usize, degrees: f64) {
        self.sprite(index).direction = degrees;
    }
    fn set_position(&mut self, index: usize, x: f64, y: f64) {
        let (old_x, old_y) = {
            let item = self.sprite(index);
            (item.x, item.y)
        };
        if self.pen_active {
            let color = self.pen_color;
            let size = self.pen_size;
            self.lines.push(BfLine {
                x1: old_x, y1: old_y, x2: x, y2: y, color, size,
            });
            if self.lines.len() > 5000 { self.lines.remove(0); }
        }
        let item = self.sprite(index);
        item.x = x; item.y = y;
    }
    fn set_x(&mut self, index: usize, x: f64) { self.sprite(index).x = x; }
    fn set_y(&mut self, index: usize, y: f64) { self.sprite(index).y = y; }
    fn change_x(&mut self, index: usize, amount: f64) { self.sprite(index).x += amount; }
    fn change_y(&mut self, index: usize, amount: f64) { self.sprite(index).y += amount; }
    fn point_towards(&mut self, index: usize, target: isize) {
        let pointer = (self.pointer_x, self.pointer_y);
        let other = if target >= 0 && (target as usize) < self.sprites.len() {
            let s = &self.sprites[target as usize];
            (s.x, s.y)
        } else { pointer };
        let item = self.sprite(index);
        item.direction = (other.0 - item.x).atan2(other.1 - item.y) * 180.0 / BF_PI;
        item.direction = item.direction.rem_euclid(360.0);
    }
    fn glide(&mut self, index: usize, x: f64, y: f64, seconds: f64) {
        let start = self.sprite(index);
        let (start_x, start_y) = (start.x, start.y);
        let begin = bf_ticks();
        let duration = (seconds.max(0.0) * 1000.0) as u32;
        loop {
            let elapsed = (bf_ticks() - begin) as f64;
            let ratio = if duration == 0 { 1.0 } else { (elapsed / duration as f64).min(1.0) };
            self.set_position(index, start_x + (x - start_x) * ratio,
                              start_y + (y - start_y) * ratio);
            if ratio >= 1.0 || !self.running.load(Ordering::SeqCst) { break; }
            unsafe { SDL_Delay(16); }
        }
    }
    fn bounce_edge(&mut self, index: usize) {
        if !self.touching_edge(index) { return; }
        let (half, x, direction) = {
            let item = self.sprite(index);
            (bf_visual_radius(item.size), item.x, item.direction)
        };
        let right = self.width as f64 / 2.0;
        let top = self.height as f64 / 2.0;
        let x_edge = x.abs() + half >= right;
        let item = self.sprite(index);
        item.direction = if x_edge { -direction } else { 180.0 - direction };
        item.direction = item.direction.rem_euclid(360.0);
        item.x = item.x.max(-right + half).min(right - half);
        item.y = item.y.max(-top + half).min(top - half);
    }
    fn show(&mut self, index: usize) { self.sprite(index).visible = true; }
    fn hide(&mut self, index: usize) { self.sprite(index).visible = false; }
    fn set_size(&mut self, index: usize, size: f64) { self.sprite(index).size = size; }
    fn change_size(&mut self, index: usize, amount: f64) { self.sprite(index).size += amount; }
    fn set_costume(&mut self, index: usize, costume: f64) {
        let item = self.sprite(index);
        let count = item.costume_count.max(1) as f64;
        item.costume = costume.max(1.0).min(count) as usize;
    }
    fn next_costume(&mut self, index: usize) {
        let item = self.sprite(index);
        item.costume = item.costume % item.costume_count.max(1) + 1;
    }
    fn say(&mut self, index: usize, message: Value, seconds: f64) {
        let text = message.as_text();
        let item = self.sprite(index);
        item.say_text = text.clone();
        item.say_until = bf_ticks() + (seconds.max(0.0) * 1000.0) as u32;
        bf_print_text(&text);
    }
    fn set_background(&mut self, color: Value) { self.background = color.as_text(); }
    fn tone(&self, frequency: f64, seconds: f64) {
        let state = AUDIO.get_or_init(|| Mutex::new(AudioState { freq: 0.0, left: 0.0, phase: 0.0 }));
        {
            let mut audio = state.lock().unwrap();
            audio.freq = frequency;
            audio.left = seconds + 0.05;
        }
        unsafe { SDL_Delay((seconds.max(0.0) * 1000.0) as u32); }
    }
    fn stop_tones(&self) {
        let state = AUDIO.get_or_init(|| Mutex::new(AudioState { freq: 0.0, left: 0.0, phase: 0.0 }));
        let mut audio = state.lock().unwrap();
        audio.freq = 0.0; audio.left = 0.0;
    }
    fn pen_down(&mut self) { self.pen_active = true; }
    fn pen_up(&mut self) { self.pen_active = false; }
    fn pen_clear(&mut self) { self.lines.clear(); }
    fn pen_set_color(&mut self, color: Value) { self.pen_color = bf_color(&color.as_text()); }
    fn pen_set_size(&mut self, size: f64) { self.pen_size = size.max(1.0).min(12.0) as i32; }
    fn init_audio(&mut self) {
        let spec = BfAudioSpec {
            freq: 44100, format: AUDIO_S16SYS, channels: 1, silence: 0,
            samples: 512, size: 0, callback: Some(bf_audio_callback),
            userdata: ptr::null_mut(),
        };
        let mut obtained = BfAudioSpec {
            freq: 0, format: 0, channels: 0, silence: 0,
            samples: 0, size: 0, callback: None, userdata: ptr::null_mut(),
        };
        unsafe {
            self.audio_device = SDL_OpenAudioDevice(ptr::null(), 0, &spec, &mut obtained, 0);
            if self.audio_device != 0 { SDL_PauseAudioDevice(self.audio_device, 0); }
        }
    }
    fn close_audio(&mut self) {
        if self.audio_device != 0 {
            unsafe { SDL_CloseAudioDevice(self.audio_device); }
        }
    }
    fn update_input(&mut self, keys: &[bool; 256], mouse: (i32, i32)) {
        self.keys = *keys;
        self.pointer_x = mouse.0 as f64 - self.width as f64 / 2.0;
        self.pointer_y = self.height as f64 / 2.0 - mouse.1 as f64;
    }
    fn random_range(&mut self, low: f64, high: f64) -> f64 {
        let (low, high) = if low <= high { (low, high) } else { (high, low) };
        let mut x = self.rng_state;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.rng_state = if x == 0 { 0x2545f491 } else { x };
        let fraction = (x >> 11) as f64 / (0x1fffffffffffff_u64 as f64);
        low + fraction * (high - low)
    }
    fn draw(&mut self, renderer: *mut c_void) {
        let bg = bf_color(&self.background);
        unsafe {
            SDL_SetRenderDrawColor(renderer, bg.0, bg.1, bg.2, 255);
            SDL_RenderClear(renderer);
        }
        for line in &self.lines {
            let color = line.color;
            unsafe { SDL_SetRenderDrawColor(renderer, color.0, color.1, color.2, 255); }
            for thickness in 0..line.size {
                let offset = thickness / 2;
                unsafe {
                    SDL_RenderDrawLine(renderer,
                        (self.width as f64 / 2.0 + line.x1) as i32 + offset,
                        (self.height as f64 / 2.0 - line.y1) as i32,
                        (self.width as f64 / 2.0 + line.x2) as i32 + offset,
                        (self.height as f64 / 2.0 - line.y2) as i32);
                }
            }
        }
        let now = bf_ticks();
        let mut sprites: Vec<BfSprite> = self.sprites.iter().cloned().collect();
        sprites.sort_by(|a, b| a.layer.cmp(&b.layer).then(a.name.cmp(&b.name)));
        for item in &sprites {
            if !item.visible { continue; }
            let size = (item.size / 100.0 * 36.0).max(4.0) as i32;
            let cx = self.width / 2 + item.x as i32;
            let cy = self.height / 2 - item.y as i32;
            let mut color = bf_color(&item.color);
            for _ in 1..item.costume {
                let swap = color.0; color.0 = color.1; color.1 = color.2; color.2 = swap;
            }
            unsafe {
                SDL_SetRenderDrawColor(renderer, color.0, color.1, color.2, 255);
                if item.shape == "rect" {
                    let rect = BfRect { x: cx - size / 2, y: cy - size / 2, w: size, h: size };
                    SDL_RenderFillRect(renderer, &rect);
                } else if item.shape == "triangle" {
                    let half = size / 2;
                    for dy in -half..=half {
                        let ratio = (dy + half) as f64 / size as f64;
                        let row_half = (ratio * size as f64 / 2.0) as i32;
                        let rect = BfRect { x: cx - row_half, y: cy + dy,
                                            w: row_half * 2, h: 1 };
                        SDL_RenderFillRect(renderer, &rect);
                    }
                } else if item.shape == "star" {
                    bf_draw_star(renderer, cx, cy, size);
                } else {
                    let radius = (size / 2).max(1);
                    for dy in -radius..=radius {
                        let dx = ((radius * radius - dy * dy) as f64).sqrt() as i32;
                        let rect = BfRect { x: cx - dx, y: cy + dy, w: dx * 2, h: 1 };
                        SDL_RenderFillRect(renderer, &rect);
                    }
                }
                if item.say_until > now {
                    let bubble = BfRect { x: cx - 34, y: cy - size - 26, w: 68, h: 20 };
                    SDL_RenderDrawRect(renderer, &bubble);
                    let tail = BfRect { x: cx - 2, y: cy - size - 6, w: 8, h: 6 };
                    SDL_RenderDrawRect(renderer, &tail);
                }
            }
        }
        unsafe { SDL_RenderPresent(renderer); }
    }
}

type SharedApp = Arc<Mutex<App>>;

trait AppExt {
    fn var_num(&self, name: &str) -> f64;
    fn var_text(&self, name: &str) -> String;
    fn var_bool(&self, name: &str) -> bool;
    fn set_var(&self, name: &str, value: Value);
    fn change_var(&self, name: &str, amount: Value);
    fn num(&self, value: Value) -> f64;
    fn text(&self, value: Value) -> String;
    fn as_bool(&self, value: Value) -> bool;
    fn join(&self, left: Value, right: Value) -> String;
    fn equal(&self, left: Value, right: Value) -> bool;
    fn not_equal(&self, left: Value, right: Value) -> bool;
    fn length(&self, value: Value) -> f64;
    fn abs_num(&self, value: f64) -> f64;
    fn sqrt_num(&self, value: f64) -> f64;
    fn sin_num(&self, value: f64) -> f64;
    fn cos_num(&self, value: f64) -> f64;
    fn round_num(&self, value: f64) -> f64;
    fn floor_num(&self, value: f64) -> f64;
    fn ceil_num(&self, value: f64) -> f64;
    fn sprite_x(&self, index: usize) -> f64;
    fn sprite_y(&self, index: usize) -> f64;
    fn sprite_direction(&self, index: usize) -> f64;
    fn sprite_costume(&self, index: usize) -> f64;
    fn sprite_size(&self, index: usize) -> f64;
    fn timer(&self) -> f64;
    fn mouse_x(&self) -> f64;
    fn mouse_y(&self) -> f64;
    fn key_pressed(&self, scancode: i32) -> bool;
    fn touching_edge(&self, index: usize) -> bool;
    fn touching_sprite(&self, first: usize, second: usize) -> bool;
    fn random_range(&self, low: f64, high: f64) -> f64;
    fn is_running(&self) -> bool;
    fn running_flag(&self) -> Arc<AtomicBool>;
    fn stop_all(&self);
    fn wait(&self, seconds: f64);
    fn move_sprite(&self, index: usize, steps: f64);
    fn turn(&self, index: usize, degrees: f64);
    fn set_direction(&self, index: usize, degrees: f64);
    fn set_position(&self, index: usize, x: f64, y: f64);
    fn set_x(&self, index: usize, x: f64);
    fn set_y(&self, index: usize, y: f64);
    fn change_x(&self, index: usize, amount: f64);
    fn change_y(&self, index: usize, amount: f64);
    fn point_towards(&self, index: usize, target: isize);
    fn glide(&self, index: usize, x: f64, y: f64, seconds: f64);
    fn bounce_edge(&self, index: usize);
    fn show(&self, index: usize);
    fn hide(&self, index: usize);
    fn set_size(&self, index: usize, size: f64);
    fn change_size(&self, index: usize, amount: f64);
    fn set_costume(&self, index: usize, costume: f64);
    fn next_costume(&self, index: usize);
    fn say(&self, index: usize, message: Value, seconds: f64);
    fn set_background(&self, color: Value);
    fn print_line(&self, value: Value);
    fn tone(&self, frequency: f64, seconds: f64);
    fn stop_tones(&self);
    fn pen_down(&self);
    fn pen_up(&self);
    fn pen_clear(&self);
    fn pen_set_color(&self, color: Value);
    fn pen_set_size(&self, size: f64);
}

impl AppExt for SharedApp {
    fn var_num(&self, name: &str) -> f64 {
        self.lock().unwrap().vars.get(name).map(|v| v.as_num()).unwrap_or(0.0)
    }
    fn var_text(&self, name: &str) -> String {
        self.lock().unwrap().vars.get(name).map(|v| v.as_text()).unwrap_or_default()
    }
    fn var_bool(&self, name: &str) -> bool {
        self.lock().unwrap().vars.get(name).map(|v| v.as_bool()).unwrap_or(false)
    }
    fn set_var(&self, name: &str, value: Value) {
        self.lock().unwrap().vars.insert(name.to_string(), value);
    }
    fn change_var(&self, name: &str, amount: Value) {
        let mut app = self.lock().unwrap();
        let current = app.vars.get(name).map(|v| v.as_num()).unwrap_or(0.0);
        app.vars.insert(name.to_string(), Value::num(current + amount.as_num()));
    }
    fn num(&self, value: Value) -> f64 { value.as_num() }
    fn text(&self, value: Value) -> String { value.as_text() }
    fn as_bool(&self, value: Value) -> bool { value.as_bool() }
    fn join(&self, left: Value, right: Value) -> String { left.as_text() + &right.as_text() }
    fn equal(&self, left: Value, right: Value) -> bool {
        self.lock().unwrap().equal(left, right)
    }
    fn not_equal(&self, left: Value, right: Value) -> bool {
        self.lock().unwrap().not_equal(left, right)
    }
    fn length(&self, value: Value) -> f64 { value.as_text().chars().count() as f64 }
    fn abs_num(&self, value: f64) -> f64 { value.abs() }
    fn sqrt_num(&self, value: f64) -> f64 { value.max(0.0).sqrt() }
    fn sin_num(&self, value: f64) -> f64 { value.sin() }
    fn cos_num(&self, value: f64) -> f64 { value.cos() }
    fn round_num(&self, value: f64) -> f64 { value.round() }
    fn floor_num(&self, value: f64) -> f64 { value.floor() }
    fn ceil_num(&self, value: f64) -> f64 { value.ceil() }
    fn sprite_x(&self, index: usize) -> f64 { self.lock().unwrap().sprite(index).x }
    fn sprite_y(&self, index: usize) -> f64 { self.lock().unwrap().sprite(index).y }
    fn sprite_direction(&self, index: usize) -> f64 { self.lock().unwrap().sprite(index).direction }
    fn sprite_costume(&self, index: usize) -> f64 { self.lock().unwrap().sprite(index).costume as f64 }
    fn sprite_size(&self, index: usize) -> f64 { self.lock().unwrap().sprite(index).size }
    fn timer(&self) -> f64 { self.lock().unwrap().timer() }
    fn mouse_x(&self) -> f64 { self.lock().unwrap().mouse_x() }
    fn mouse_y(&self) -> f64 { self.lock().unwrap().mouse_y() }
    fn key_pressed(&self, scancode: i32) -> bool {
        self.lock().unwrap().keys.get(scancode as usize).copied().unwrap_or(false)
    }
    fn touching_edge(&self, index: usize) -> bool { self.lock().unwrap().touching_edge(index) }
    fn touching_sprite(&self, first: usize, second: usize) -> bool {
        self.lock().unwrap().touching_sprite(first, second)
    }
    fn random_range(&self, low: f64, high: f64) -> f64 {
        self.lock().unwrap().random_range(low, high)
    }
    fn is_running(&self) -> bool { self.lock().unwrap().running.load(Ordering::SeqCst) }
    fn running_flag(&self) -> Arc<AtomicBool> { self.lock().unwrap().running.clone() }
    fn stop_all(&self) { self.lock().unwrap().running.store(false, Ordering::SeqCst); }
    fn wait(&self, seconds: f64) {
        let until = std::time::Instant::now() + Duration::from_secs_f64(seconds.max(0.0));
        while self.is_running() && std::time::Instant::now() < until {
            thread::sleep(Duration::from_millis(5));
        }
    }
    fn move_sprite(&self, index: usize, steps: f64) { self.lock().unwrap().move_sprite(index, steps); }
    fn turn(&self, index: usize, degrees: f64) { self.lock().unwrap().turn(index, degrees); }
    fn set_direction(&self, index: usize, degrees: f64) { self.lock().unwrap().set_direction(index, degrees); }
    fn set_position(&self, index: usize, x: f64, y: f64) { self.lock().unwrap().set_position(index, x, y); }
    fn set_x(&self, index: usize, x: f64) { self.lock().unwrap().set_x(index, x); }
    fn set_y(&self, index: usize, y: f64) { self.lock().unwrap().set_y(index, y); }
    fn change_x(&self, index: usize, amount: f64) { self.lock().unwrap().change_x(index, amount); }
    fn change_y(&self, index: usize, amount: f64) { self.lock().unwrap().change_y(index, amount); }
    fn point_towards(&self, index: usize, target: isize) { self.lock().unwrap().point_towards(index, target); }
    fn glide(&self, index: usize, x: f64, y: f64, seconds: f64) {
        let (start_x, start_y) = {
            let mut app = self.lock().unwrap();
            let sprite = app.sprite(index);
            (sprite.x, sprite.y)
        };
        let begin = bf_ticks();
        let duration = (seconds.max(0.0) * 1000.0) as u32;
        loop {
            let elapsed = (bf_ticks() - begin) as f64;
            let ratio = if duration == 0 {
                1.0
            } else {
                (elapsed / duration as f64).min(1.0)
            };
            self.set_position(index, start_x + (x - start_x) * ratio,
                              start_y + (y - start_y) * ratio);
            if ratio >= 1.0 || !self.is_running() { break; }
            thread::sleep(Duration::from_millis(16));
        }
    }
    fn bounce_edge(&self, index: usize) { self.lock().unwrap().bounce_edge(index); }
    fn show(&self, index: usize) { self.lock().unwrap().show(index); }
    fn hide(&self, index: usize) { self.lock().unwrap().hide(index); }
    fn set_size(&self, index: usize, size: f64) { self.lock().unwrap().set_size(index, size); }
    fn change_size(&self, index: usize, amount: f64) { self.lock().unwrap().change_size(index, amount); }
    fn set_costume(&self, index: usize, costume: f64) { self.lock().unwrap().set_costume(index, costume); }
    fn next_costume(&self, index: usize) { self.lock().unwrap().next_costume(index); }
    fn say(&self, index: usize, message: Value, seconds: f64) { self.lock().unwrap().say(index, message, seconds); }
    fn set_background(&self, color: Value) { self.lock().unwrap().set_background(color); }
    fn print_line(&self, value: Value) { bf_print_text(&value.as_text()); }
    fn tone(&self, frequency: f64, seconds: f64) {
        let state = AUDIO.get_or_init(|| {
            Mutex::new(AudioState { freq: 0.0, left: 0.0, phase: 0.0 })
        });
        {
            let mut audio = state.lock().unwrap();
            audio.freq = frequency;
            audio.left = seconds + 0.05;
        }
        let deadline = std::time::Instant::now()
            + Duration::from_secs_f64(seconds.max(0.0));
        while self.is_running() && std::time::Instant::now() < deadline {
            thread::sleep(Duration::from_millis(5));
        }
    }
    fn stop_tones(&self) { self.lock().unwrap().stop_tones(); }
    fn pen_down(&self) { self.lock().unwrap().pen_down(); }
    fn pen_up(&self) { self.lock().unwrap().pen_up(); }
    fn pen_clear(&self) { self.lock().unwrap().pen_clear(); }
    fn pen_set_color(&self, color: Value) { self.lock().unwrap().pen_set_color(color); }
    fn pen_set_size(&self, size: f64) { self.lock().unwrap().pen_set_size(size); }
}
'''
