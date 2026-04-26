import mercantile, requests, os

# bounding box around your flying area - adjust these 
west, south, east, north = -122.31, 37.86, -122.29, 37.88
zooms = range(15, 20)  # zoom levels 15-19
out = "tiles"

for tile in mercantile.tiles(west, south, east, north, zooms=zooms):
    url = f"https://tile.openstreetmap.org/{tile.z}/{tile.x}/{tile.y}.png"
    path = f"{out}/{tile.z}/{tile.x}"
    os.makedirs(path, exist_ok=True)
    fpath = f"{path}/{tile.y}.png"
    if not os.path.exists(fpath):
        r = requests.get(url, headers={"User-Agent": "copter-viewer/1.0"})
        with open(fpath, "wb") as f:
            f.write(r.content)
        print(f"Downloaded {tile.z}/{tile.x}/{tile.y}")