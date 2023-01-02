import json

from app.abstract.files import File
from app.SuperMechs.images import AttachedImage, Attachment
from app.SuperMechs.inv_item import InvItem
from app.SuperMechs.item import Item
from app.SuperMechs.typedefs import ItemDictVer3


with open("tests/example_item_v2.json") as file:
    data: ItemDictVer3 = json.load(file)

resource = File("D:/Obrazy/Games/SuperMechs/Sprites/Heat items/OverchargedRocketBattery.png")

image, coro = AttachedImage.from_resource(resource, Attachment(0, 0))

item = Item[Attachment].from_json(data, "@darkstare", False, image)
inv_item = InvItem.from_item(item)
