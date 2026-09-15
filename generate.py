from PIL import Image
from pathlib import Path
import math
import shutil
import sys

# ============================================================
# SETTINGS
# ============================================================

TILES_X = 100
TILES_Y = 100

SOURCE_TILE_WIDTH = 1920
SOURCE_TILE_HEIGHT = 1080

OUTPUT_TILE_SIZE = 256

SOURCE = Path("source")
UPDATE = Path("update")
OUTPUT = Path("generated")

# ============================================================
# WORLD SIZE
# ============================================================

WORLD_WIDTH = TILES_X * SOURCE_TILE_WIDTH
WORLD_HEIGHT = TILES_Y * SOURCE_TILE_HEIGHT

MAX_LEVEL = math.ceil(
    math.log2(max(WORLD_WIDTH, WORLD_HEIGHT))
)

# ============================================================
# SOURCE TILE LOADING
# ============================================================

def load_source_tile(x, y):
    """
    Load a source tile.

    If the tile doesn't exist, use watertile.png instead.
    """

    path = SOURCE / f"{x}-{y}.png"

    if not path.exists():
        return Image.open(
            SOURCE / "watertile.png"
        ).convert("RGBA")

    return Image.open(path).convert("RGBA")


# ============================================================
# CREATE ONE HIGH-RES DEEP ZOOM TILE
# ============================================================

def create_highest_tile(tx, ty):

    level = MAX_LEVEL

    output_dir = (
        OUTPUT / "world_files" / str(level)
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    pixel_x = tx * OUTPUT_TILE_SIZE
    pixel_y = ty * OUTPUT_TILE_SIZE

    tile = Image.new(
        "RGBA",
        (
            OUTPUT_TILE_SIZE,
            OUTPUT_TILE_SIZE
        ),
        (0, 0, 0, 0)
    )

    # Find source tiles overlapping this output tile

    source_x_start = (
        pixel_x // SOURCE_TILE_WIDTH
    ) + 1

    source_y_start = (
        pixel_y // SOURCE_TILE_HEIGHT
    ) + 1

    source_x_end = (
        (pixel_x + OUTPUT_TILE_SIZE - 1)
        // SOURCE_TILE_WIDTH
    ) + 1

    source_y_end = (
        (pixel_y + OUTPUT_TILE_SIZE - 1)
        // SOURCE_TILE_HEIGHT
    ) + 1

    for sy in range(
        source_y_start,
        source_y_end + 1
    ):

        for sx in range(
            source_x_start,
            source_x_end + 1
        ):

            source_pixel_x = (
                (sx - 1)
                * SOURCE_TILE_WIDTH
            )

            source_pixel_y = (
                (sy - 1)
                * SOURCE_TILE_HEIGHT
            )

            left = max(
                pixel_x,
                source_pixel_x
            )

            top = max(
                pixel_y,
                source_pixel_y
            )

            right = min(
                pixel_x + OUTPUT_TILE_SIZE,
                source_pixel_x + SOURCE_TILE_WIDTH
            )

            bottom = min(
                pixel_y + OUTPUT_TILE_SIZE,
                source_pixel_y + SOURCE_TILE_HEIGHT
            )

            if left >= right or top >= bottom:
                continue

            source = load_source_tile(sx, sy)

            crop = source.crop(
                (
                    left - source_pixel_x,
                    top - source_pixel_y,
                    right - source_pixel_x,
                    bottom - source_pixel_y
                )
            )

            tile.paste(
                crop,
                (
                    left - pixel_x,
                    top - pixel_y
                )
            )

    tile.save(
        output_dir / f"{tx}_{ty}.png"
    )


# ============================================================
# CALCULATE HIGH-RES TILES AFFECTED BY SOURCE TILE
# ============================================================

def affected_highest_tiles(x, y):

    source_left = (
        (x - 1)
        * SOURCE_TILE_WIDTH
    )

    source_top = (
        (y - 1)
        * SOURCE_TILE_HEIGHT
    )

    source_right = (
        source_left
        + SOURCE_TILE_WIDTH
    )

    source_bottom = (
        source_top
        + SOURCE_TILE_HEIGHT
    )

    tx_start = (
        source_left
        // OUTPUT_TILE_SIZE
    )

    ty_start = (
        source_top
        // OUTPUT_TILE_SIZE
    )

    tx_end = (
        (source_right - 1)
        // OUTPUT_TILE_SIZE
    )

    ty_end = (
        (source_bottom - 1)
        // OUTPUT_TILE_SIZE
    )

    affected = set()

    for ty in range(
        ty_start,
        ty_end + 1
    ):

        for tx in range(
            tx_start,
            tx_end + 1
        ):

            affected.add(
                (tx, ty)
            )

    return affected


# ============================================================
# GENERATE LOWER LOD TILE
# ============================================================

def create_lower_tile(
    level,
    tx,
    ty
):

    current_dir = (
        OUTPUT
        / "world_files"
        / str(level)
    )

    child_dir = (
        OUTPUT
        / "world_files"
        / str(level + 1)
    )

    current_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    canvas = Image.new(
        "RGBA",
        (
            OUTPUT_TILE_SIZE * 2,
            OUTPUT_TILE_SIZE * 2
        ),
        (0, 0, 0, 0)
    )

    positions = [
        (0, 0, tx * 2, ty * 2),
        (256, 0, tx * 2 + 1, ty * 2),
        (0, 256, tx * 2, ty * 2 + 1),
        (256, 256, tx * 2 + 1, ty * 2 + 1),
    ]

    for px, py, cx, cy in positions:

        child = (
            child_dir
            / f"{cx}_{cy}.png"
        )

        if child.exists():

            image = Image.open(
                child
            ).convert("RGBA")

            canvas.paste(
                image,
                (px, py)
            )

    canvas = canvas.resize(
        (
            OUTPUT_TILE_SIZE,
            OUTPUT_TILE_SIZE
        ),
        Image.Resampling.LANCZOS
    )

    canvas.save(
        current_dir / f"{tx}_{ty}.png"
    )


# ============================================================
# CREATE DZI FILE
# ============================================================

def create_dzi():

    dzi = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image
    xmlns="http://schemas.microsoft.com/deepzoom/2008"
    Format="png"
    Overlap="0"
    TileSize="{OUTPUT_TILE_SIZE}">
    <Size
        Width="{WORLD_WIDTH}"
        Height="{WORLD_HEIGHT}" />
</Image>
"""

    with open(
        OUTPUT / "world.dzi",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(dzi)


# ============================================================
# HARD RUN
# ============================================================

def hard_run():

    print()
    print("======================================")
    print(" HARD RUN")
    print("======================================")
    print()

    if OUTPUT.exists():

        print("Deleting generated files...")

        shutil.rmtree(
            OUTPUT
        )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"World size: "
        f"{WORLD_WIDTH} × {WORLD_HEIGHT}"
    )

    print(
        f"Maximum level: "
        f"{MAX_LEVEL}"
    )

    # ----------------------------------------
    # Generate highest level
    # ----------------------------------------

    level = MAX_LEVEL

    tiles_x = math.ceil(
        WORLD_WIDTH
        / OUTPUT_TILE_SIZE
    )

    tiles_y = math.ceil(
        WORLD_HEIGHT
        / OUTPUT_TILE_SIZE
    )

    print()
    print(
        f"Generating level {level}..."
    )

    for ty in range(tiles_y):

        for tx in range(tiles_x):

            create_highest_tile(
                tx,
                ty
            )

        print(
            f"  {ty + 1}/{tiles_y} rows complete"
        )

    # ----------------------------------------
    # Generate lower levels
    # ----------------------------------------

    for level in range(
        MAX_LEVEL - 1,
        -1,
        -1
    ):

        width = math.ceil(
            WORLD_WIDTH
            / (2 ** (MAX_LEVEL - level))
        )

        height = math.ceil(
            WORLD_HEIGHT
            / (2 ** (MAX_LEVEL - level))
        )

        tiles_x = math.ceil(
            width / OUTPUT_TILE_SIZE
        )

        tiles_y = math.ceil(
            height / OUTPUT_TILE_SIZE
        )

        print()
        print(
            f"Generating level {level}..."
        )

        for ty in range(tiles_y):

            for tx in range(tiles_x):

                create_lower_tile(
                    level,
                    tx,
                    ty
                )

            print(
                f"  {ty + 1}/{tiles_y} rows complete"
            )

    create_dzi()

    print()
    print("======================================")
    print(" HARD RUN COMPLETE")
    print("======================================")
    print()


# ============================================================
# UPDATE RUN
# ============================================================

def update_run():

    print()
    print("======================================")
    print(" UPDATE RUN")
    print("======================================")
    print()

    if not UPDATE.exists():

        print(
            "No update folder found."
        )

        print(
            "Creating it now."
        )

        UPDATE.mkdir(
            parents=True
        )

        return

    update_files = list(
        UPDATE.glob("*.png")
    )

    # Ignore watertile.png
    update_files = [
        file
        for file in update_files
        if file.name != "watertile.png"
    ]

    if not update_files:

        print(
            "No tiles found in update/."
        )

        return

    print(
        f"Found {len(update_files)} "
        f"updated tile(s)."
    )

    # ----------------------------------------
    # Parse updated tiles
    # ----------------------------------------

    changed_tiles = []

    for file in update_files:

        try:

            name = file.stem

            x, y = map(
                int,
                name.split("-")
            )

            if not (
                1 <= x <= TILES_X
                and
                1 <= y <= TILES_Y
            ):

                print(
                    f"Skipping {file.name}: "
                    f"outside world bounds."
                )

                continue

            changed_tiles.append(
                (x, y, file)
            )

        except ValueError:

            print(
                f"Skipping {file.name}: "
                f"invalid filename."
            )

    if not changed_tiles:

        print(
            "No valid update tiles found."
        )

        return

    # ----------------------------------------
    # Make sure generated pyramid exists
    # ----------------------------------------

    highest_dir = (
        OUTPUT
        / "world_files"
        / str(MAX_LEVEL)
    )

    if not highest_dir.exists():

        print()
        print(
            "Generated pyramid does not exist."
        )

        print(
            "Run:"
        )

        print(
            "    python generate.py hard"
        )

        print(
            "first."
        )

        return

    # ----------------------------------------
    # Copy updates into SOURCE temporarily
    # ----------------------------------------

    print()
    print("Installing updated source tiles...")

    for x, y, file in changed_tiles:

        destination = (
            SOURCE
            / f"{x}-{y}.png"
        )

        shutil.copy2(
            file,
            destination
        )

    # ----------------------------------------
    # Find affected highest-level tiles
    # ----------------------------------------

    affected = set()

    for x, y, file in changed_tiles:

        affected.update(
            affected_highest_tiles(
                x,
                y
            )
        )

    print()
    print(
        f"Highest LOD tiles affected: "
        f"{len(affected)}"
    )

    # ----------------------------------------
    # Regenerate highest level
    # ----------------------------------------

    print()
    print(
        f"Updating level {MAX_LEVEL}..."
    )

    for tx, ty in affected:

        create_highest_tile(
            tx,
            ty
        )

    # ----------------------------------------
    # Propagate changes down through LODs
    # ----------------------------------------

    current_affected = affected

    for level in range(
        MAX_LEVEL - 1,
        -1,
        -1
    ):

        parents = set()

        for tx, ty in current_affected:

            parent_x = tx // 2
            parent_y = ty // 2

            parents.add(
                (
                    parent_x,
                    parent_y
                )
            )

        print()
        print(
            f"Updating level {level}..."
        )

        print(
            f"  Tiles affected: "
            f"{len(parents)}"
        )

        for tx, ty in parents:

            create_lower_tile(
                level,
                tx,
                ty
            )

        current_affected = parents

    # ----------------------------------------
    # Move updates into source
    # ----------------------------------------

    print()
    print(
        "Moving update files into source..."
    )

    for x, y, file in changed_tiles:

        destination = (
            SOURCE
            / file.name
        )

        # The file was already copied above.
        # Now remove the update copy.

        if file.exists():

            file.unlink()

    create_dzi()

    print()
    print("======================================")
    print(" UPDATE COMPLETE")
    print("======================================")
    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    hard = (
        len(sys.argv) > 1
        and sys.argv[1].lower() == "hard"
    )

    if hard:

        hard_run()

    else:

        update_run()