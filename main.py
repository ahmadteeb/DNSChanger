import sdl2
import sdl2.ext
import sdl2.sdlttf
import os
import subprocess
import json
import time
import math
import sys

# Initialize SDL2 and TTF
sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK)
sdl2.sdlttf.TTF_Init()

# Get current display mode for scaling
display_mode = sdl2.SDL_DisplayMode()
sdl2.SDL_GetCurrentDisplayMode(0, display_mode)
SCREEN_WIDTH = display_mode.w
SCREEN_HEIGHT = display_mode.h

# Use full screen size
WINDOW_WIDTH = SCREEN_WIDTH
WINDOW_HEIGHT = SCREEN_HEIGHT

# Calculate scaling factors based on original design (1280x720)
SCALE_X = WINDOW_WIDTH / 1280
SCALE_Y = WINDOW_HEIGHT / 720

# Scale other constants
CONTENT_WIDTH = int(1000 * SCALE_X)
BUTTON_HEIGHT = int(60 * SCALE_Y)
BUTTON_PADDING = int(15 * SCALE_Y)
ANIMATION_SPEED = 0.3
SCROLL_SPEED = 20
SCROLL_ACCELERATION = 1.2
SCROLL_DECELERATION = 0.8
MAX_SCROLL_SPEED = 30
SCROLL_MARGIN = int(200 * SCALE_Y)
HEADER_HEIGHT = int(120 * SCALE_Y)

# Colors
DARK_BG = sdl2.SDL_Color(18, 18, 18)  # Dark background
DARKER_BG = sdl2.SDL_Color(12, 12, 12)  # Slightly darker for contrast
ACCENT_BLUE = sdl2.SDL_Color(0, 149, 255)  # Bright blue for accents
LIGHT_BLUE = sdl2.SDL_Color(0, 170, 255)  # Lighter blue for hover
WHITE = sdl2.SDL_Color(255, 255, 255)  # Pure white for text
LIGHT_GRAY = sdl2.SDL_Color(200, 200, 200)  # Light gray for secondary text
DARK_GRAY = sdl2.SDL_Color(40, 40, 40)  # Dark gray for buttons
SUCCESS_GREEN = sdl2.SDL_Color(76, 175, 80)  # Success message color
SCROLLBAR_BG = sdl2.SDL_Color(30, 30, 30)  # Scrollbar background
SCROLLBAR_THUMB = sdl2.SDL_Color(60, 60, 60)  # Scrollbar thumb

# Controller button mapping (Trimui Smart Pro)
CONTROLLER_BUTTON_A = 1      
CONTROLLER_BUTTON_B = 0

# D-pad button mappings
CONTROLLER_BUTTON_UP = 1     
CONTROLLER_BUTTON_DOWN = 4   
CONTROLLER_BUTTON_LEFT = 8  
CONTROLLER_BUTTON_RIGHT = 2 

DNS_LIST_PATH = os.environ.get('DNS_LIST_PATH')
RESOLV_FILE_PATH = os.environ.get('RESOLV_FILE_PATH')

class DNSChanger:
    def __init__(self):
        # Create window at position 0,0 to fill the entire screen
        self.window = sdl2.ext.Window(
            "DNS Changer",
            size=(WINDOW_WIDTH, WINDOW_HEIGHT),
            position=(0, 0)
        )
        
        num_joysticks = sdl2.SDL_NumJoysticks()
        self.joystick = sdl2.SDL_JoystickOpen(0) if num_joysticks else None
    
        self.window.show()

        self.renderer = sdl2.ext.Renderer(self.window)
        self.factory = sdl2.ext.SpriteFactory(sdl2.ext.TEXTURE, renderer=self.renderer)
        
        # Load fonts with scaled sizes
        font_path = 'assets/fonts/arial.ttf'
        min_font_scale = min(SCALE_X, SCALE_Y)
        self.title_font = sdl2.sdlttf.TTF_OpenFont(font_path.encode(), int(32 * min_font_scale))
        self.font = sdl2.sdlttf.TTF_OpenFont(font_path.encode(), int(20 * min_font_scale))
        self.small_font = sdl2.sdlttf.TTF_OpenFont(font_path.encode(), int(16 * min_font_scale))
        
        self.dns_list = self.load_dns_list()
        self.selected_index = 0
        self.hover_index = -1
        self.running = True
        self.animation_progress = 0
        self.last_time = time.time()
        self.show_success = False
        self.success_time = 0
        self.scroll_offset = 0
        self.target_scroll = 0
        self.scroll_velocity = 0
        self.scroll_direction = 0

    def load_dns_list(self):
        dns_entries = []
        
        # Add Default DNS option
        dns_entries.append({
            'name': 'Default DNS',
            'primary': 'auto',
            'secondary': 'auto'
        })
        
        if not os.path.exists(DNS_LIST_PATH):
            return []

        try:
            with open(DNS_LIST_PATH, 'r') as f:
                dns_entries += json.load(f)
                
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in dns_list.json")
            return []
        
        
        
        return dns_entries

    def render_text(self, text, font, color):
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            font, text.encode(), color
        )
        text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer.sdlrenderer, text_surface)
        width = text_surface.contents.w
        height = text_surface.contents.h
        sdl2.SDL_FreeSurface(text_surface)
        return text_texture, width, height

    def draw_rounded_rect(self, rect, color, radius=10):
        # Draw main rectangle
        inner_rect = sdl2.SDL_Rect(rect.x + radius, rect.y, rect.w - 2 * radius, rect.h)
        self.renderer.fill(inner_rect, color)
        
        # Draw vertical rectangles
        side_rect = sdl2.SDL_Rect(rect.x, rect.y + radius, radius, rect.h - 2 * radius)
        self.renderer.fill(side_rect, color)
        side_rect.x = rect.x + rect.w - radius
        self.renderer.fill(side_rect, color)

    def calculate_scroll_target(self):
        # Calculate the position of the selected item
        item_y = self.selected_index * (BUTTON_HEIGHT + BUTTON_PADDING)
        
        # Calculate the visible area (excluding header)
        visible_height = WINDOW_HEIGHT - HEADER_HEIGHT
        
        # Calculate the total content height
        total_height = len(self.dns_list) * (BUTTON_HEIGHT + BUTTON_PADDING)
        
        # Calculate the maximum possible scroll
        max_scroll = max(0, total_height - visible_height)
        
        # Calculate the target scroll position
        if item_y < self.scroll_offset + SCROLL_MARGIN:
            # Item is above the visible area
            return max(0, item_y - SCROLL_MARGIN)
        elif item_y + BUTTON_HEIGHT > self.scroll_offset + visible_height - SCROLL_MARGIN:
            # Item is below the visible area
            target = item_y - visible_height + BUTTON_HEIGHT + SCROLL_MARGIN
            return min(max_scroll, max(0, target))
        return self.scroll_offset

    def update_scroll(self, dt):
        # Calculate target scroll
        self.target_scroll = self.calculate_scroll_target()
        
        # Calculate distance to target
        distance = self.target_scroll - self.scroll_offset
        
        # Update scroll velocity based on distance
        if abs(distance) > 1:
            # Accelerate towards target
            self.scroll_velocity = min(
                MAX_SCROLL_SPEED,
                self.scroll_velocity + SCROLL_ACCELERATION * math.copysign(1, distance)
            )
        else:
            # Decelerate when close to target
            self.scroll_velocity *= SCROLL_DECELERATION
            if abs(self.scroll_velocity) < 0.1:
                self.scroll_velocity = 0
                self.scroll_offset = self.target_scroll
        
        # Apply velocity and clamp to bounds
        self.scroll_offset += self.scroll_velocity * dt * 60
        
        # Calculate maximum scroll
        visible_height = WINDOW_HEIGHT - HEADER_HEIGHT
        total_height = len(self.dns_list) * (BUTTON_HEIGHT + BUTTON_PADDING)
        max_scroll = max(0, total_height - visible_height)
        
        # Clamp scroll offset
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

    def draw(self):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Update animation
        self.animation_progress = min(1.0, self.animation_progress + dt / ANIMATION_SPEED)
        
        # Update scroll
        self.update_scroll(dt)

        # Clear background with dark color
        self.renderer.clear(DARK_BG)

        # Draw title
        title_texture, title_width, title_height = self.render_text(
            "DNS Changer", self.title_font, WHITE
        )
        title_rect = sdl2.SDL_Rect(
            (WINDOW_WIDTH - title_width) // 2,
            int(30 * SCALE_Y),
            title_width,
            title_height
        )
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, title_texture, None, title_rect)
        sdl2.SDL_DestroyTexture(title_texture)

        # Draw subtitle
        subtitle_texture, sub_width, sub_height = self.render_text(
            "Select a DNS configuration to apply", self.small_font, LIGHT_GRAY
        )
        sub_rect = sdl2.SDL_Rect(
            (WINDOW_WIDTH - sub_width) // 2,
            int(70 * SCALE_Y),
            sub_width,
            sub_height
        )
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, subtitle_texture, None, sub_rect)
        sdl2.SDL_DestroyTexture(subtitle_texture)

        # Calculate content area
        content_x = (WINDOW_WIDTH - CONTENT_WIDTH) // 2
        content_y = HEADER_HEIGHT
        
        # Calculate total height and visible area
        visible_height = WINDOW_HEIGHT - HEADER_HEIGHT
        total_height = len(self.dns_list) * (BUTTON_HEIGHT + BUTTON_PADDING)
        
        # Draw scroll indicator if content is larger than visible area
        if total_height > visible_height:
            # Calculate scrollbar position and size
            scrollbar_height = max(int(30 * SCALE_Y), (visible_height / total_height) * visible_height)
            scrollbar_y = (self.scroll_offset / total_height) * (visible_height - scrollbar_height)
            
            # Draw scrollbar background
            scrollbar_bg = sdl2.SDL_Rect(
                WINDOW_WIDTH - int(20 * SCALE_X),
                HEADER_HEIGHT,
                int(8 * SCALE_X),
                visible_height
            )
            self.renderer.fill(scrollbar_bg, SCROLLBAR_BG)
            
            # Draw scrollbar thumb
            scrollbar_thumb = sdl2.SDL_Rect(
                WINDOW_WIDTH - int(20 * SCALE_X),
                HEADER_HEIGHT + int(scrollbar_y),
                int(8 * SCALE_X),
                int(scrollbar_height)
            )
            self.renderer.fill(scrollbar_thumb, SCROLLBAR_THUMB)
        
        # Create a clipping rectangle for the content area
        clip_rect = sdl2.SDL_Rect(
            content_x,
            HEADER_HEIGHT,
            CONTENT_WIDTH,
            visible_height
        )
        sdl2.SDL_RenderSetClipRect(self.renderer.sdlrenderer, clip_rect)
        
        # Draw content with scroll offset
        for i, dns in enumerate(self.dns_list):
            y_pos = content_y + i * (BUTTON_HEIGHT + BUTTON_PADDING) - int(self.scroll_offset)
            
            # Skip if outside visible area
            if y_pos + BUTTON_HEIGHT < HEADER_HEIGHT or y_pos > WINDOW_HEIGHT:
                continue

            # Button background
            button_rect = sdl2.SDL_Rect(
                content_x,
                y_pos,
                CONTENT_WIDTH,
                BUTTON_HEIGHT
            )

            if i == self.selected_index:
                # Selected item animation
                progress = math.sin(self.animation_progress * math.pi / 2)
                color = sdl2.ext.Color(
                    int(DARK_GRAY.r + (ACCENT_BLUE.r - DARK_GRAY.r) * progress),
                    int(DARK_GRAY.g + (ACCENT_BLUE.g - DARK_GRAY.g) * progress),
                    int(DARK_GRAY.b + (ACCENT_BLUE.b - DARK_GRAY.b) * progress)
                )
                self.draw_rounded_rect(button_rect, color, int(10 * min(SCALE_X, SCALE_Y)))
                text_color = WHITE
            else:
                self.draw_rounded_rect(button_rect, DARK_GRAY, int(10 * min(SCALE_X, SCALE_Y)))
                text_color = LIGHT_GRAY

            # DNS name
            text_texture, width, height = self.render_text(dns['name'], self.font, text_color)
            text_rect = sdl2.SDL_Rect(
                content_x + int(20 * SCALE_X),
                y_pos + (BUTTON_HEIGHT - height) // 2,
                width,
                height
            )
            sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, text_texture, None, text_rect)
            sdl2.SDL_DestroyTexture(text_texture)

            # DNS details
            if dns['name'] != 'Default DNS':
                details = f"Primary: {dns['primary']}  -  Secondary: {dns['secondary']}"
            else:
                details = "System default DNS configuration"
                
            detail_texture, d_width, d_height = self.render_text(
                details, self.small_font, LIGHT_GRAY if text_color == LIGHT_GRAY else WHITE
            )
            detail_rect = sdl2.SDL_Rect(
                content_x + CONTENT_WIDTH - d_width - int(20 * SCALE_X),
                y_pos + (BUTTON_HEIGHT - d_height) // 2,
                d_width,
                d_height
            )
            sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, detail_texture, None, detail_rect)
            sdl2.SDL_DestroyTexture(detail_texture)

        # Reset clipping rectangle
        sdl2.SDL_RenderSetClipRect(self.renderer.sdlrenderer, None)

        # Draw success message if needed
        if self.show_success:
            if time.time() - self.success_time < 2.0:
                msg_texture, msg_width, msg_height = self.render_text(
                    "DNS configuration applied successfully!", self.font, SUCCESS_GREEN
                )
                msg_rect = sdl2.SDL_Rect(
                    (WINDOW_WIDTH - msg_width) // 2,
                    WINDOW_HEIGHT - int(60 * SCALE_Y),
                    msg_width,
                    msg_height
                )
                sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, msg_texture, None, msg_rect)
                sdl2.SDL_DestroyTexture(msg_texture)
            else:
                self.show_success = False
                if hasattr(self, 'close_after_success') and self.close_after_success:
                    self.running = False

        self.renderer.present()

    def set_dns(self, dns_entry):
        with open(RESOLV_FILE_PATH, "r") as f:
            lines = f.readlines()
        for line in lines.copy():
            if line.startswith('nameserver'):
                lines.remove(line)
                
        if dns_entry['name'] == 'Default DNS':
            default_dns = subprocess.getoutput("ip r | awk '/default/ {print $3}'")
            lines.append(f"nameserver {default_dns}\n")
        else:
            lines.append(f"nameserver {dns_entry['primary']}\n")
            lines.append(f"nameserver {dns_entry['secondary']}\n")
            
        subprocess.run(['chattr', '-i', RESOLV_FILE_PATH], check=False)
        with open(RESOLV_FILE_PATH, 'w') as f:
            f.writelines(lines)
        subprocess.run(['chattr', '+i', RESOLV_FILE_PATH], check=False)
        
        self.show_success = True
        self.success_time = time.time()
        self.close_after_success = True  # New flag to indicate we should close after success

    def run(self):
        while self.running:
            events = sdl2.ext.get_events()
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    self.running = False
                    break
                
                elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                    self._handle_controller_button(event.jbutton.button)
                    
                elif event.type == sdl2.SDL_JOYHATMOTION:
                    self._handle_d_pad_controller_button(event.jhat.value)
                
                elif event.type == sdl2.SDL_KEYDOWN:
                    self._handle_normal_input(event.key.keysym.sym)

            self.draw()
            sdl2.SDL_Delay(16)  # Cap at ~60 FPS

    
    def _handle_controller_button(self, button):
        # Map controller buttons to keyboard events
        button_map = {
            CONTROLLER_BUTTON_A: sdl2.SDLK_RETURN,
            CONTROLLER_BUTTON_B: sdl2.SDLK_BACKSPACE,
        }
        
        if button in button_map:
            return self._handle_normal_input(button_map[button])
        return True

    def _handle_d_pad_controller_button(self, button):
        # Map controller buttons to keyboard events
        button_map = {
            CONTROLLER_BUTTON_UP: sdl2.SDLK_UP,
            CONTROLLER_BUTTON_DOWN: sdl2.SDLK_DOWN,
            CONTROLLER_BUTTON_LEFT: sdl2.SDLK_LEFT,
            CONTROLLER_BUTTON_RIGHT: sdl2.SDLK_RIGHT
        }
        
        if button in button_map:
            return self._handle_normal_input(button_map[button])
        return True
    
    def _handle_normal_input(self, key):
        if key == sdl2.SDLK_UP:
            self.selected_index = max(0, self.selected_index - 1)
            self.animation_progress = 0
        elif key == sdl2.SDLK_DOWN:
            self.selected_index = min(len(self.dns_list) - 1, self.selected_index + 1)
            self.animation_progress = 0
        elif key == sdl2.SDLK_RETURN:
            if 0 <= self.selected_index < len(self.dns_list):
                self.set_dns(self.dns_list[self.selected_index])
        elif key == sdl2.SDLK_BACKSPACE:
            self.running = False
    
    def cleanup(self):
        if self.joystick:
            sdl2.SDL_JoystickClose(self.joystick)
        sdl2.sdlttf.TTF_CloseFont(self.font)
        sdl2.sdlttf.TTF_CloseFont(self.title_font)
        sdl2.sdlttf.TTF_CloseFont(self.small_font)
        sdl2.sdlttf.TTF_Quit()
        sdl2.SDL_Quit()

if __name__ == "__main__":
    app = DNSChanger()
    try:
        if not getattr(sys, 'frozen', False):
            from dotenv import load_dotenv
            load_dotenv()
        app.run()
    finally:
        app.cleanup() 