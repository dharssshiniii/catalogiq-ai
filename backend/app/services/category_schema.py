from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryField:
    key: str
    output_column: str
    aliases: tuple[str, ...] = ()


DISHWASHER_SCHEMA = [
    CategoryField("manufacturer", "MANUFACTURER_NAME"), CategoryField("brand", "BRAND_NAME"),
    CategoryField("manufacturer_part_number", "MANUFACTURER_PART_NUMBER"), CategoryField("classpath", "Classpath"),
    CategoryField("series", "TRADE_NAME"), CategoryField("product_name", "Product Name"),
    CategoryField("wash_cycles", "ATTRIBUTE_VALUE 1"), CategoryField("voltage", "ATTRIBUTE_VALUE 2"),
    CategoryField("amperage", "ATTRIBUTE_VALUE 3"), CategoryField("mounting_type", "ATTRIBUTE_VALUE 4"),
    CategoryField("plug_type", "ATTRIBUTE_VALUE 5"), CategoryField("size", "ATTRIBUTE_VALUE 6"),
    CategoryField("depth_door_open", "ATTRIBUTE_VALUE 7"), CategoryField("minimum_height", "ATTRIBUTE_VALUE 8"),
    CategoryField("maximum_height", "ATTRIBUTE_VALUE 9"), CategoryField("sound_level", "ATTRIBUTE_VALUE 10"),
    CategoryField("material", "ATTRIBUTE_VALUE 11"), CategoryField("colour", "ATTRIBUTE_VALUE 12"),
    CategoryField("additional_information", "Additional information"), CategoryField("approvals", "Standard/Approvals"),
    CategoryField("warranty", "Warranty"), CategoryField("features", "ITEM_FEATURES_1"),
    CategoryField("product_image", "Product Image"), CategoryField("specification_sheet", "Specification Sheet"),
]

CATEGORY_SCHEMAS = {"built_in_dishwasher": DISHWASHER_SCHEMA}
