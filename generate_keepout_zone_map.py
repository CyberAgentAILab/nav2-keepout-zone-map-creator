import argparse

from nav2_keepoutzonemap_creator import Nav2KeepoutZoneMapCreator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map', help='Path to Occupancy Gridmap.', required=True)
    parser.add_argument('--bev', help='Path to BEV image.', required=True)
    args = parser.parse_args()
    Nav2KeepoutZoneMapCreator(args.map, args.bev)


if __name__ == "__main__":
    main()
