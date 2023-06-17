import orjson

from files import File

# from supermechs.images import AttachedImage, Attachment
from supermechs.api import InvItem, Item
from supermechs.typedefs import ItemDictVer3

with open("tests/example_item_v2.json") as file:
    data: ItemDictVer3 = orjson.loads(file.read())

resource = File("./data/OverchargedRocketBattery.png")

# image, coro = AttachedImage.from_resource(resource, Attachment(0, 0))

item = Item.from_json(data, "@darkstare", False)
inv_item = InvItem.from_item(item, maxed=True)
