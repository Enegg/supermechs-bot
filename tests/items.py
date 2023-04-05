import orjson

from app.abstract.files import File
# from app.SuperMechs.images import AttachedImage, Attachment
from app.SuperMechs.inv_item import InvItem
from app.SuperMechs.item import Item
from app.SuperMechs.typedefs import ItemDictVer3


with open("tests/example_item_v2.json") as file:
    data: ItemDictVer3 = orjson.loads(file.read())

resource = File("./data/OverchargedRocketBattery.png")

# image, coro = AttachedImage.from_resource(resource, Attachment(0, 0))

item = Item.from_json(data, "@darkstare", False)
inv_item = InvItem.from_item(item, maxed=True)
