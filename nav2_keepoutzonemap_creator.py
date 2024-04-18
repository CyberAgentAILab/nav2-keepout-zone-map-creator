import os

import cv2
import dearpygui.dearpygui as dpg
import numpy as np


class Nav2KeepoutZoneMapCreator:
    """Nav2KeepoutZoneMapCreator class
    """
    def __init__(self, map_name: str, bev_name: str):
        """initialize Nav2KeepoutZoneMapCreator class

        Args:
            map_name (str): filepath of Map image
            bev_name (str): filepath of BEV image
        """
        # map image
        self.map_name = map_name
        self.map_img = cv2.imread(map_name, cv2.IMREAD_COLOR)
        map_height, map_width, _ = self.map_img.shape[:3]
        map_img_is_landscape = (map_width > map_height)
        self.map_texture = self.convert2texture(self.map_img)

        # BEV image
        self.bev_img = cv2.imread(bev_name, cv2.IMREAD_COLOR)
        bev_height, bev_width, _ = self.bev_img.shape[:3]
        bev_img_is_landscape = (bev_width > bev_height)
        if map_img_is_landscape != bev_img_is_landscape:
            self.bev_img = cv2.rotate(self.bev_img, cv2.ROTATE_90_CLOCKWISE)
            bev_height, bev_width, _ = self.bev_img.shape[:3]
        scale = float(map_height) / float(bev_height)
        self.bev_img = cv2.resize(self.bev_img, None, fx=scale, fy=scale)
        bev_height, bev_width, _ = self.bev_img.shape[:3]
        self.bev_img_with_margin = np.full((map_height, map_width, 3), (255, 255, 255), np.uint8)
        self.bev_img_with_margin[0:bev_height, 0:bev_width] = self.bev_img

        # keepout zone map image
        self.keepout_zone_map_img = cv2.imread(map_name, cv2.IMREAD_UNCHANGED)

        # preview image
        self.preview_img = None

        # initialize mask image
        self.mask_img = np.zeros((map_height, map_width), np.uint8)

        # initialize points
        self.points = np.empty((0, 2), dtype=np.int32)

        # initialize Dear PyGui
        self.gui_init(map_width, map_height)

    def convert2texture(self, img: np.ndarray) -> np.ndarray:
        """convert from image to texture for Dear PyGui

        Args:
            img (np.ndarray): image

        Returns:
            np.ndarray: texture
        """
        rgba_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        rgba_img_float = rgba_img.astype(np.float32)
        rgba_img_float /= 255.0
        return rgba_img_float

    def update_texture(self):
        """update texture
        """
        # get parameters
        alpha = dpg.get_value("alpha_float")
        x_shift = dpg.get_value("x_shift_int")
        y_shift = dpg.get_value("y_shift_int")
        rotation = dpg.get_value("rotation_int")
        scale = dpg.get_value("scale_float")

        height, width, _ = self.bev_img_with_margin.shape
        mat = np.array([[1, 0, x_shift], [0, 1, y_shift]], dtype=np.float32)
        temp = cv2.warpAffine(self.bev_img_with_margin, mat, (width, height))
        mat = cv2.getRotationMatrix2D((width / 2, height / 2), -rotation, scale)
        temp = cv2.warpAffine(temp, mat, (width, height))

        # alpha blending
        self.preview_img = cv2.addWeighted(temp, alpha, self.map_img, (1.0 - alpha), 0.0)
        self.preview_img[self.mask_img == 255] = [0, 0, 255]
        preview_texture = self.convert2texture(self.preview_img)

        # set texture
        dpg.set_value("texture", preview_texture)

    def gui_init(self, map_width: int, map_height: int):
        """initialize GUI

        Args:
            map_width (int): width of map image
            map_height (int): height of map image
        """
        dpg.create_context()
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(width=map_width, height=map_height, default_value=self.map_texture, tag="texture")

        with dpg.window(label="Image", tag="window"):
            dpg.add_image("texture", tag="image")
            dpg.add_slider_float(label="alpha", default_value=0.5, min_value=0.0, max_value=1.0, tag="alpha_float", callback=self.param_callback)
            dpg.add_slider_int(label="X shift(pix)", default_value=0, min_value=-1000, max_value=1000, tag="x_shift_int", callback=self.param_callback)
            dpg.add_slider_int(label="Y shift(pix)", default_value=0, min_value=-1000, max_value=1000, tag="y_shift_int", callback=self.param_callback)
            dpg.add_slider_int(label="rotation(deg)", default_value=0, min_value=-180, max_value=180, tag="rotation_int", callback=self.param_callback)
            dpg.add_slider_float(label="scale", default_value=1.0, min_value=0.0, max_value=2.0, tag="scale_float", callback=self.param_callback)
            dpg.add_button(label="Save", callback=self.save_button_callback)

        with dpg.item_handler_registry(tag="image_handler_registry"):
            dpg.add_item_clicked_handler(callback=self.mouse_left_callback, button=dpg.mvMouseButton_Left)
        dpg.bind_item_handler_registry("image", "image_handler_registry")

        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self.key_press_callback)

        self.update_texture()

        dpg.create_viewport(title='Keepout Zone Map Creator', width=1000, height=1000)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def param_callback(self, sender: str, app_data: int):
        """callback function that user change parameters

        Args:
            sender (str): sender
            app_data (int): app_data
        """
        self.update_texture()

    def mouse_left_callback(self, sender: str, app_data: int):
        """callback function of mouse click(left button)

        Args:
            sender (str): sender
            app_data (int): app_data
        """
        # calculate clicked position
        origin_pos = dpg.get_item_rect_min(app_data[1])
        mouse_pos = dpg.get_mouse_pos(local=False)
        x = int(mouse_pos[0]) - origin_pos[0]
        y = int(mouse_pos[1]) - origin_pos[1]

        # draw clicked position
        self.points = np.append(self.points, np.array([[x, y]], dtype=np.int32), axis=0)
        cv2.circle(self.mask_img, (x, y), 5, color=(255), thickness=-1)

        # update preview image
        self.preview_img[self.mask_img == 255] = [0, 0, 255]
        self.update_texture()

    def finish_add_vertices(self):
        """finish_add_vertices
        """
        # update preview image
        cv2.polylines(self.mask_img, self.points.reshape(1, -1, 2), isClosed=True, color=(255), thickness=2)
        self.preview_img[self.mask_img == 255] = [0, 0, 255]

        # update keepout zone map
        cv2.fillPoly(self.keepout_zone_map_img, self.points.reshape(1, -1, 2), color=(0), lineType=cv2.LINE_8, shift=0)

        # reset points
        self.points = np.empty((0, 2), dtype=np.int32)

        # update image
        self.update_texture()

    def key_press_callback(self, sender: str, app_data: int):
        """callback function of keyboard

        Args:
            sender (str): sender
            app_data (int): app_data
        """
        if app_data == dpg.mvKey_F:
            self.finish_add_vertices()
        elif app_data == dpg.mvKey_Q:
            dpg.stop_dearpygui()

    def save_button_callback(self, sender: str, app_data: int):
        """callback function of save button

        Args:
            sender (str): sender
            app_data (int): app_data
        """
        print("Save keepout zone map.")

        basename = os.path.basename(self.map_name)
        basename_without_ext = os.path.splitext(os.path.basename(basename))[0]
        keepout_zone_map_filename = f"{basename_without_ext}_keepout.pgm"
        cv2.imwrite(keepout_zone_map_filename, self.keepout_zone_map_img)
