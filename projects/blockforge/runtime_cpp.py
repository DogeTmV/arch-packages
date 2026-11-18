"""C++ runtime embedded in every generated blockforge program.

The runtime is deliberately self-contained.  It needs only a C++17 compiler
and SDL2; no headers, images, or libraries from the editor are required at
run time, so generated source can be moved to another machine and built there.
"""

SOURCE = r'''
// --- blockforge runtime ----------------------------------------------------
static const double BF_PI = 3.14159265358979323846;

struct Value {
    enum Kind { NUMBER, TEXT, BOOLEAN } kind;
    double number;
    std::string text;
    bool boolean;

    Value(double value = 0) : kind(NUMBER), number(value), boolean(false) {}
    Value(int value) : kind(NUMBER), number(value), boolean(false) {}
    Value(const std::string& value) : kind(TEXT), number(0), text(value), boolean(false) {}
    Value(const char* value) : kind(TEXT), number(0), text(value), boolean(false) {}
    Value(bool value) : kind(BOOLEAN), number(value ? 1 : 0), boolean(value) {}

    std::string as_text() const {
        if (kind == TEXT) return text;
        if (kind == BOOLEAN) return boolean ? "true" : "false";
        double rounded = std::round(number);
        if (std::isfinite(number) &&
            std::fabs(number - rounded) <=
                1e-12 * std::max(1.0, std::fabs(number))) {
            char buffer[64];
            std::snprintf(buffer, sizeof(buffer), "%lld", (long long)rounded);
            return std::string(buffer);
        }
        char buffer[64];
        auto result = std::to_chars(buffer, buffer + sizeof(buffer), number);
        if (result.ec == std::errc()) {
            return std::string(buffer, result.ptr);
        }
        std::snprintf(buffer, sizeof(buffer), "%.15g", number);
        std::string formatted(buffer);
        return formatted == "-0" ? "0" : formatted;
    }
    double as_num() const {
        if (kind == NUMBER) return number;
        if (kind == BOOLEAN) return boolean ? 1 : 0;
        try {
            std::size_t consumed = 0;
            double parsed = std::stod(text, &consumed);
            while (consumed < text.size() &&
                   std::isspace((unsigned char)text[consumed])) ++consumed;
            return consumed == text.size() ? parsed : 0;
        } catch (...) { return 0; }
    }
    bool as_bool() const {
        if (kind == BOOLEAN) return boolean;
        if (kind == NUMBER) return number != 0;
        return !text.empty();
    }
};

// Scratch-style "stop this script" is thread-local so it also propagates out
// of a called custom block without ending the whole program.
static thread_local bool bf_stopping = false;
static void bf_reset_script() { bf_stopping = false; }
static bool bf_should_stop() { return bf_stopping; }
static void bf_stop_script() { bf_stopping = true; }

static std::array<int, 3> bf_color(const std::string& value) {
    if (value.size() >= 7 && value[0] == '#') {
        return {
            (int)std::strtol(value.substr(1, 2).c_str(), nullptr, 16),
            (int)std::strtol(value.substr(3, 2).c_str(), nullptr, 16),
            (int)std::strtol(value.substr(5, 2).c_str(), nullptr, 16)
        };
    }
    return {124, 108, 255};
}

static int bf_utf8_length(const std::string& text) {
    int count = 0;
    for (unsigned char byte : text) {
        if ((byte & 0xC0) != 0x80) ++count;
    }
    return count;
}

static double bf_visual_radius(double size) {
    return std::max(4.0, size / 100.0 * 36.0) / 2.0;
}

static void bf_print_text(const std::string& text) {
    std::string normalized = text;
    std::size_t end = normalized.size();
    if (end && normalized[end - 1] == '\n') --end;
    if (end && normalized[end - 1] == '\r') --end;
    normalized.erase(end);
    if (normalized.empty()) {
        std::cout << std::endl;
        return;
    }
    std::string line;
    for (char byte : normalized) {
        if (byte == '\n') {
            std::cout << line << std::endl;
            line.clear();
        } else if (byte != '\r') {
            line.push_back(byte);
        }
    }
    std::cout << line << std::endl;
}

static void bf_draw_star(SDL_Renderer* renderer, int cx, int cy, int size) {
    const int point_count = 10;
    std::array<std::pair<int, int>, point_count> points;
    for (int index = 0; index < point_count; ++index) {
        double radius = size / 2.0 * (index % 2 ? 0.45 : 1.0);
        double angle = (-90 + index * 36) * BF_PI / 180.0;
        points[index] = {
            cx + (int)std::lround(std::cos(angle) * radius),
            cy + (int)std::lround(std::sin(angle) * radius),
        };
    }
    int lowest = points[0].second, highest = points[0].second;
    for (const auto& point : points) {
        lowest = std::min(lowest, point.second);
        highest = std::max(highest, point.second);
    }
    for (int y = lowest; y <= highest; ++y) {
        std::vector<double> crossings;
        for (int index = 0; index < point_count; ++index) {
            int x1 = points[index].first, y1 = points[index].second;
            int x2 = points[(index + 1) % point_count].first;
            int y2 = points[(index + 1) % point_count].second;
            if ((y1 <= y && y2 > y) || (y2 <= y && y1 > y)) {
                crossings.push_back(x1 + (y - y1) * (double)(x2 - x1) /
                                    (double)(y2 - y1));
            }
        }
        std::sort(crossings.begin(), crossings.end());
        for (std::size_t index = 0; index + 1 < crossings.size(); index += 2) {
            SDL_RenderDrawLine(renderer, (int)std::ceil(crossings[index]), y,
                               (int)std::floor(crossings[index + 1]), y);
        }
    }
    for (int index = 0; index < point_count; ++index) {
        const auto& first = points[index];
        const auto& second = points[(index + 1) % point_count];
        SDL_RenderDrawLine(renderer, first.first, first.second,
                           second.first, second.second);
    }
}

struct BfLine {
    double x1, y1, x2, y2;
    std::array<int, 3> color;
    int size;
};

struct BfImage {
    int width = 0, height = 0;
    std::vector<Uint8> rgba;
};

struct BfSprite {
    std::string name;
    double x = 0, y = 0, size = 100, direction = 90;
    bool visible = true;
    int costume = 1, costume_count = 2, layer = 0;
    std::string shape = "circle";
    std::string color = "#4c9ffe";
    std::string image;
    Uint32 say_until = 0;
    std::string say_text;
};

static std::mutex g_audio_mutex;
static double g_tone_freq = 0;
static double g_tone_left = 0;
static double g_tone_phase = 0;

static void bf_audio_callback(void*, Uint8* stream, int length) {
    std::lock_guard<std::mutex> guard(g_audio_mutex);
    Sint16* samples = reinterpret_cast<Sint16*>(stream);
    int count = length / (int)sizeof(Sint16);
    for (int i = 0; i < count; ++i) {
        if (g_tone_freq > 0 && g_tone_left > 0) {
            double wave = std::sin(2 * BF_PI * g_tone_phase * g_tone_freq);
            samples[i] = (Sint16)(wave * 12000.0);
            g_tone_phase += 1.0 / 44100.0;
        } else {
            samples[i] = 0;
        }
    }
    g_tone_left -= (double)length / (44100.0 * 2.0);
    if (g_tone_left < 0) g_tone_left = 0;
}

class App {
public:
    int width, height;
    std::string background = "#151a26";
    std::string backdrop;
    std::vector<BfSprite> sprites;
    std::vector<BfLine> lines;
    std::unordered_map<std::string, BfImage> images;
    std::unordered_map<std::string, SDL_Texture*> textures;
    std::unordered_map<std::string, Value> vars;
    std::mutex mutex;
    std::atomic<bool> running{true};
    std::array<bool, 256> keys{};
    int pointer_x = 0, pointer_y = 0;
    Uint32 started = 0;
    std::mt19937 generator;
    Uint32 audio_device = 0;
    bool pen_active = false;
    std::array<int, 3> pen_color{{74, 222, 128}};
    int pen_size = 3;

    App(int stage_width, int stage_height, const std::string& stage_color)
        : width(stage_width), height(stage_height), background(stage_color) {
        started = SDL_GetTicks();
        generator.seed(SDL_GetTicks());
        keys.fill(false);
    }

    BfSprite& sprite(int index) {
        if (sprites.empty()) sprites.push_back(BfSprite());
        return sprites[(std::size_t)index % sprites.size()];
    }

    void add_image(const std::string& id, int image_width, int image_height,
                   const Uint8* pixels, std::size_t length) {
        BfImage image;
        image.width = image_width;
        image.height = image_height;
        image.rgba.assign(pixels, pixels + length);
        images[id] = std::move(image);
    }

    void set_background(const std::string& color) {
        background = color;
        backdrop.clear();
    }

    void set_backdrop(const std::string& id) {
        backdrop = id;
    }

    SDL_Texture* texture_for(SDL_Renderer* renderer, const std::string& id) {
        if (id.empty()) return nullptr;
        auto cached = textures.find(id);
        if (cached != textures.end()) return cached->second;
        auto found = images.find(id);
        if (found == images.end()) return nullptr;
        const BfImage& image = found->second;
        SDL_Texture* texture = SDL_CreateTexture(
            renderer, SDL_PIXELFORMAT_RGBA8888, SDL_TEXTUREACCESS_STATIC,
            image.width, image.height);
        if (!texture) return nullptr;
        SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND);
        SDL_UpdateTexture(texture, nullptr, image.rgba.data(), image.width * 4);
        textures[id] = texture;
        return texture;
    }

    void clear_textures() {
        for (auto& item : textures) {
            if (item.second) SDL_DestroyTexture(item.second);
        }
        textures.clear();
    }

    double num(const Value& value) const { return value.as_num(); }
    std::string text(const Value& value) const { return value.as_text(); }
    bool as_bool(const Value& value) const { return value.as_bool(); }
    std::string join(const Value& left, const Value& right) const {
        return left.as_text() + right.as_text();
    }
    bool equal(const Value& left, const Value& right) const {
        if (left.kind == Value::TEXT && right.kind == Value::TEXT)
            return left.text == right.text;
        return left.as_num() == right.as_num();
    }
    bool not_equal(const Value& left, const Value& right) const {
        return !equal(left, right);
    }
    double length(const Value& value) const {
        return (double)bf_utf8_length(value.as_text());
    }
    double abs_num(double value) const { return std::fabs(value); }
    double sqrt_num(double value) const {
        return std::sqrt(std::max(0.0, value));
    }
    double sin_num(double value) const { return std::sin(value); }
    double cos_num(double value) const { return std::cos(value); }
    double round_num(double value) const {
        return std::round(value);
    }
    double floor_num(double value) const {
        return std::floor(value);
    }
    double ceil_num(double value) const {
        return std::ceil(value);
    }

    double var_num(const std::string& name) {
        std::lock_guard<std::mutex> guard(mutex);
        auto found = vars.find(name);
        return found == vars.end() ? 0 : found->second.as_num();
    }
    std::string var_text(const std::string& name) {
        std::lock_guard<std::mutex> guard(mutex);
        auto found = vars.find(name);
        return found == vars.end() ? std::string() : found->second.as_text();
    }
    bool var_bool(const std::string& name) {
        std::lock_guard<std::mutex> guard(mutex);
        auto found = vars.find(name);
        return found != vars.end() && found->second.as_bool();
    }
    void set_var(const std::string& name, const Value& value) {
        std::lock_guard<std::mutex> guard(mutex);
        vars[name] = value;
    }
    void change_var(const std::string& name, const Value& amount) {
        std::lock_guard<std::mutex> guard(mutex);
        double current = vars.count(name) ? vars[name].as_num() : 0;
        vars[name] = Value(current + amount.as_num());
    }

    double sprite_x(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        return sprite(index).x;
    }
    double sprite_y(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        return sprite(index).y;
    }
    double sprite_direction(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        return sprite(index).direction;
    }
    double sprite_costume(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        return sprite(index).costume;
    }
    double sprite_size(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        return sprite(index).size;
    }
    double timer() const {
        return (double)(SDL_GetTicks() - started) / 1000.0;
    }
    double mouse_x() const { return pointer_x; }
    double mouse_y() const { return pointer_y; }

    bool key_pressed(int scancode) {
        std::lock_guard<std::mutex> guard(mutex);
        return scancode >= 0 && scancode < 256 && keys[scancode];
    }
    bool touching_edge(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        double half = bf_visual_radius(item.size);
        return std::fabs(item.x) + half >= width / 2.0 ||
               std::fabs(item.y) + half >= height / 2.0;
    }
    bool touching_sprite(int first, int second) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& a = sprite(first);
        BfSprite& b = sprite(second);
        double dx = a.x - b.x, dy = a.y - b.y;
        double distance = std::sqrt(dx * dx + dy * dy);
        return distance < (a.size + b.size) / 4.0;
    }
    double random_range(double low, double high) {
        std::lock_guard<std::mutex> guard(mutex);
        if (high < low) std::swap(low, high);
        std::uniform_real_distribution<double> distribution(low, high);
        return distribution(generator);
    }
    void update_input() {
        const Uint8* state = SDL_GetKeyboardState(nullptr);
        int mx = 0, my = 0;
        SDL_GetMouseState(&mx, &my);
        std::lock_guard<std::mutex> guard(mutex);
        if (state) {
            for (int i = 0; i < 256; ++i) keys[i] = state[i] != 0;
        }
        pointer_x = mx - width / 2;
        pointer_y = height / 2 - my;
    }
    bool is_running() const { return running.load(); }
    void stop_all() { running.store(false); }
    void wait(double seconds) {
        Uint32 until = SDL_GetTicks() + (Uint32)std::max(0.0, seconds * 1000.0);
        while (running.load() && SDL_GetTicks() < until) SDL_Delay(5);
    }

    void move(int index, double steps) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        double radians = item.direction * BF_PI / 180.0;
        double nx = item.x + std::sin(radians) * steps;
        double ny = item.y + std::cos(radians) * steps;
        if (pen_active) {
            BfLine line;
            line.x1 = item.x; line.y1 = item.y;
            line.x2 = nx; line.y2 = ny;
            line.color = pen_color; line.size = pen_size;
            lines.push_back(line);
            if (lines.size() > 5000) lines.erase(lines.begin());
        }
        item.x = nx; item.y = ny;
    }
    void turn(int index, double degrees) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        item.direction += degrees;
        while (item.direction >= 360) item.direction -= 360;
        while (item.direction < 0) item.direction += 360;
    }
    void set_direction(int index, double degrees) {
        std::lock_guard<std::mutex> guard(mutex);
        sprite(index).direction = degrees;
    }
    void set_position(int index, double x, double y) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        if (pen_active) {
            BfLine line;
            line.x1 = item.x; line.y1 = item.y;
            line.x2 = x; line.y2 = y;
            line.color = pen_color; line.size = pen_size;
            lines.push_back(line);
            if (lines.size() > 5000) lines.erase(lines.begin());
        }
        item.x = x; item.y = y;
    }
    void set_x(int index, double x) {
        std::lock_guard<std::mutex> guard(mutex);
        sprite(index).x = x;
    }
    void set_y(int index, double y) {
        std::lock_guard<std::mutex> guard(mutex);
        sprite(index).y = y;
    }
    void change_x(int index, double amount) {
        std::lock_guard<std::mutex> guard(mutex);
        sprite(index).x += amount;
    }
    void change_y(int index, double amount) {
        std::lock_guard<std::mutex> guard(mutex);
        sprite(index).y += amount;
    }
    void point_towards(int index, int target) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        double tx = pointer_x, ty = pointer_y;
        if (target >= 0 && (std::size_t)target < sprites.size()) {
            tx = sprites[target].x; ty = sprites[target].y;
        }
        item.direction = std::atan2(tx - item.x, ty - item.y) * 180.0 / BF_PI;
        if (item.direction < 0) item.direction += 360;
    }
    void glide(int index, double x, double y, double seconds) {
        double start_x = sprite_x(index), start_y = sprite_y(index);
        Uint32 begin = SDL_GetTicks();
        Uint32 duration = (Uint32)std::max(0.0, seconds * 1000.0);
        while (running.load()) {
            double elapsed = (double)(SDL_GetTicks() - begin);
            double ratio = duration == 0 ? 1 : std::min(1.0, elapsed / duration);
            set_position(index, start_x + (x - start_x) * ratio,
                         start_y + (y - start_y) * ratio);
            if (ratio >= 1) break;
            SDL_Delay(16);
        }
    }
    void bounce_edge(int index) {
        bool edge = touching_edge(index);
        if (!edge) return;
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        double half = bf_visual_radius(item.size);
        if (std::fabs(item.x) + half >= width / 2.0)
            item.direction = -item.direction;
        else
            item.direction = 180 - item.direction;
        while (item.direction < 0) item.direction += 360;
        while (item.direction >= 360) item.direction -= 360;
        item.x = std::max(-width / 2.0 + half,
                          std::min(width / 2.0 - half, item.x));
        item.y = std::max(-height / 2.0 + half,
                          std::min(height / 2.0 - half, item.y));
    }
    void show(int index) { std::lock_guard<std::mutex> guard(mutex); sprite(index).visible = true; }
    void hide(int index) { std::lock_guard<std::mutex> guard(mutex); sprite(index).visible = false; }
    void set_size(int index, double size) { std::lock_guard<std::mutex> guard(mutex); sprite(index).size = size; }
    void change_size(int index, double amount) { std::lock_guard<std::mutex> guard(mutex); sprite(index).size += amount; }
    void set_costume(int index, double costume) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        int count = std::max(1, item.costume_count);
        item.costume = (int)std::max(1.0, std::min((double)count, std::floor(costume)));
    }
    void next_costume(int index) {
        std::lock_guard<std::mutex> guard(mutex);
        BfSprite& item = sprite(index);
        item.costume = item.costume % std::max(1, item.costume_count) + 1;
    }
    void say(int index, const Value& message, double seconds) {
        std::string text;
        {
            std::lock_guard<std::mutex> guard(mutex);
            BfSprite& item = sprite(index);
            text = message.as_text();
            item.say_text = text;
            item.say_until = SDL_GetTicks() + (Uint32)std::max(0.0, seconds * 1000.0);
        }
        bf_print_text(text);
    }
    void set_background(const Value& color) {
        std::lock_guard<std::mutex> guard(mutex);
        background = color.as_text();
        backdrop.clear();
    }
    void set_backdrop(const Value& id) {
        std::lock_guard<std::mutex> guard(mutex);
        backdrop = id.as_text();
    }
    void print_line(const Value& value) {
        bf_print_text(value.as_text());
    }
    void tone(double frequency, double seconds) {
        {
            std::lock_guard<std::mutex> guard(g_audio_mutex);
            g_tone_freq = frequency;
            g_tone_left = seconds + 0.05;
        }
        Uint32 remaining = (Uint32)std::max(0.0, seconds * 1000.0);
        while (remaining > 0 && running.load()) {
            Uint32 slice = std::min(remaining, (Uint32)10);
            SDL_Delay(slice);
            remaining -= slice;
        }
    }
    void stop_tones() {
        std::lock_guard<std::mutex> guard(g_audio_mutex);
        g_tone_freq = 0; g_tone_left = 0;
    }
    void pen_down() { std::lock_guard<std::mutex> guard(mutex); pen_active = true; }
    void pen_up() { std::lock_guard<std::mutex> guard(mutex); pen_active = false; }
    void pen_clear() { std::lock_guard<std::mutex> guard(mutex); lines.clear(); }
    void pen_set_color(const Value& color) {
        std::lock_guard<std::mutex> guard(mutex);
        pen_color = bf_color(color.as_text());
    }
    void pen_set_size(double size) {
        std::lock_guard<std::mutex> guard(mutex);
        pen_size = (int)std::max(1.0, std::min(12.0, size));
    }
    void init_audio() {
        SDL_AudioSpec desired;
        SDL_zero(desired);
        desired.freq = 44100;
        desired.format = AUDIO_S16SYS;
        desired.channels = 1;
        desired.samples = 512;
        desired.callback = bf_audio_callback;
        SDL_AudioSpec obtained;
        audio_device = SDL_OpenAudioDevice(nullptr, 0, &desired, &obtained, 0);
        if (audio_device) SDL_PauseAudioDevice(audio_device, 0);
    }
    void close_audio() {
        if (audio_device) SDL_CloseAudioDevice(audio_device);
    }

    void draw_shape(SDL_Renderer* renderer, const BfSprite& item,
                    int cx, int cy, int size, std::array<int, 3> color) {
        SDL_SetRenderDrawColor(renderer, color[0], color[1], color[2], 255);
        if (item.shape == "rect") {
            SDL_Rect box{cx - size / 2, cy - size / 2, size, size};
            SDL_RenderFillRect(renderer, &box);
        } else if (item.shape == "triangle") {
            for (int dy = -size / 2; dy <= size / 2; ++dy) {
                double ratio = (dy + size / 2.0) / (double)size;
                int half = (int)(ratio * size / 2.0);
                SDL_Rect row{cx - half, cy + dy, half * 2, 1};
                SDL_RenderFillRect(renderer, &row);
            }
        } else if (item.shape == "star") {
            bf_draw_star(renderer, cx, cy, size);
        } else {
            int radius = std::max(1, size / 2);
            for (int dy = -radius; dy <= radius; ++dy) {
                int dx = (int)std::sqrt((double)(radius * radius - dy * dy));
                SDL_Rect row{cx - dx, cy + dy, dx * 2, 1};
                SDL_RenderFillRect(renderer, &row);
            }
        }
    }

    void draw(SDL_Renderer* renderer) {
        std::lock_guard<std::mutex> guard(mutex);
        auto bg = bf_color(background);
        SDL_SetRenderDrawColor(renderer, bg[0], bg[1], bg[2], 255);
        SDL_RenderClear(renderer);
        if (SDL_Texture* backdrop_texture = texture_for(renderer, backdrop)) {
            SDL_Rect stage{0, 0, width, height};
            SDL_RenderCopy(renderer, backdrop_texture, nullptr, &stage);
        }
        for (const BfLine& line : lines) {
            SDL_SetRenderDrawColor(renderer, line.color[0], line.color[1],
                                   line.color[2], 255);
            for (int thickness = 0; thickness < line.size; ++thickness) {
                SDL_RenderDrawLine(renderer,
                    (int)(width / 2 + line.x1) + thickness / 2,
                    (int)(height / 2 - line.y1),
                    (int)(width / 2 + line.x2) + thickness / 2,
                    (int)(height / 2 - line.y2));
            }
        }
        std::vector<BfSprite> ordered = sprites;
        std::stable_sort(ordered.begin(), ordered.end(),
                         [](const BfSprite& a, const BfSprite& b) {
                             if (a.layer != b.layer) return a.layer < b.layer;
                             return a.name < b.name;
                         });
        for (const BfSprite& item : ordered) {
            if (!item.visible) continue;
            int size = (int)std::max(4.0, item.size / 100.0 * 36.0);
            int cx = width / 2 + (int)item.x;
            int cy = height / 2 - (int)item.y;
            auto color = bf_color(item.color);
            for (int costume = 1; costume < item.costume; ++costume) {
                std::swap(color[0], color[1]);
                std::swap(color[1], color[2]);
            }
            if (SDL_Texture* texture = texture_for(renderer, item.image)) {
                SDL_Rect box{cx - size / 2, cy - size / 2, size, size};
                SDL_RenderCopyEx(renderer, texture, nullptr, &box,
                                 90.0 - item.direction, nullptr, SDL_FLIP_NONE);
            } else {
                draw_shape(renderer, item, cx, cy, size, color);
            }
            if (item.say_until > SDL_GetTicks()) {
                SDL_SetRenderDrawColor(renderer, 245, 247, 252, 255);
                SDL_Rect bubble{cx - 34, cy - size - 26, 68, 20};
                SDL_RenderDrawRect(renderer, &bubble);
                SDL_Rect tail{cx - 2, cy - size - 6, 8, 6};
                SDL_RenderDrawRect(renderer, &tail);
            }
        }
        SDL_RenderPresent(renderer);
    }
};
'''
