import json

from SuperMechs.inv_item import InvItem
from SuperMechs.item import Item
from SuperMechs.pack_versioning import ItemDictVer3

with open("tests/example_item_v3.json") as file:
    data: ItemDictVer3 = json.load(file)

item = Item[None].from_json_v2(
    data,
    {
        "base_url": "https://raw.githubusercontent.com/ctrl-raul/supermechs-item-images/master/reloaded/png/"
    },
)
inv_item = InvItem.from_item(item)
