import argparse
import os

import cv2
import numpy as np
import open3d as o3d


def crop_pointcloud(pcd: o3d.geometry.PointCloud, bbox: o3d.geometry.AxisAlignedBoundingBox) -> o3d.geometry.PointCloud:
    """crop point cloud

    Args:
        pcd (o3d.geometry.PointCloud): 3D PointCloud
        bbox (o3d.geometry.AxisAlignedBoundingBox): 3D BoundingBox

    Returns:
        o3d.geometry.PointCloud: cropped 3D PointCloud
    """
    cropped_pcd = pcd.crop(bbox)
    return cropped_pcd


# reference http://ronny.rest/tutorials/module/pointclouds_01/point_cloud_birdseye/
def pointcloud2birdseye(pcd: o3d.geometry.PointCloud, min_bound: np.ndarray,
                        max_bound: np.ndarray, resolution: float = 0.05) -> np.ndarray:
    """converts 3D PointCloud from to BEV image

    Args:
        pcd (o3d.geometry.PointCloud): 3D PointCloud
        min_bound (np.ndarray): min bound(meter)
        max_bound (np.ndarray): max bound(meter)
        resolution (float, optional): resolution. Defaults to 0.05(meter).

    Returns:
        np.ndarray: BEV image
    """
    points = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors) * 255

    x_points = points[:, 0]
    y_points = points[:, 1]

    x_img = (x_points / resolution).astype(np.int32)
    y_img = (-y_points / resolution).astype(np.int32)
    x_img -= np.amin(x_img)
    y_img -= np.amin(y_img)
    x_max = 1 + int((max_bound[0] - min_bound[0]) / resolution)
    y_max = 1 + int((max_bound[1] - min_bound[1]) / resolution)

    bev_img = np.full([y_max, x_max, 3], (255, 255, 255), np.uint8)
    bev_img[y_img, x_img] = colors

    return bev_img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Path to PoindCloud Map.', required=True)
    parser.add_argument('--min_z', type=float, default=-2.0, help='min_z(meter)', required=False)
    parser.add_argument('--max_z', type=float, default=2.0, help='max_z(meter)', required=False)
    parser.add_argument('--vis', help='Visualize generated BEV image.', action='store_true')
    args = parser.parse_args()

    filepath = args.input
    pcd = o3d.io.read_point_cloud(filepath)

    # crop point cloud
    bbox = pcd.get_axis_aligned_bounding_box()
    min_bound = bbox.get_min_bound()
    max_bound = bbox.get_max_bound()
    min_z = args.min_z
    max_z = args.max_z
    min_bound[2] = min_z
    max_bound[2] = max_z
    bbox_height = o3d.geometry.AxisAlignedBoundingBox(
        min_bound.reshape(3, 1),
        max_bound.reshape(3, 1),
    )
    cropped_pcd = crop_pointcloud(pcd, bbox_height)

    # generate birdseye view
    bev_img = pointcloud2birdseye(cropped_pcd, min_bound, max_bound)

    # convert color space for OpenCV
    bev_img_bgr = cv2.cvtColor(bev_img, cv2.COLOR_RGB2BGR)

    # apply median filter
    bev_img_bgr = cv2.medianBlur(bev_img_bgr, 3)

    basename = os.path.basename(filepath)
    basename_without_ext = os.path.splitext(os.path.basename(basename))[0]
    cv2.imwrite(f"{basename_without_ext}_birdseye.png", bev_img_bgr)

    if args.vis:
        # visualization
        cv2.imshow("bev_img_bgr", bev_img_bgr)
        cv2.waitKey(0)


if __name__ == "__main__":
    main()
