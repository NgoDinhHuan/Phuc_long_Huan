from enum import Enum


class WarehouseLabelName(Enum):
    # forklift
    FORKLIFT = "forklift"
    HAND_PALLET_JACK = "hand_pallet_jack"
    ELECTRIC_PALLET_JACK = "electric_pallet_jack"
    REACH_TRUCK = "reach_truck"
    PALLET_TRUCK = "pallet_truck"
    LOAD_CARRIER = "load_carrier"

    # truck
    TRUCK = "truck"

    # pallet, package, product
    BOX = "box"
    PALLET = "pallet"
    PALLET_WITH_BOX = "pallet_with_box"
    PALLET_PACKAGE = "pallet_package"
    PRODUCT_BOX = "product_box"
    PRODUCT_PACKAGE = "product_package"

    # person
    FACE = "head"
    PERSON = "person"
    PERSON_VISIBLE_CLOTHES = "person_visible_clothes"
    PERSON_USE_PHONE = "person_use_phone"
    PERSON_EAT_DRINK = "person_eat_drink"
    PERSON_CARRY_OBJECT = "person_carry_object"
    SECURITY_PERSON = "security_person"

    # other object
    STILLAGE = "stillage"
    ALCOHOL_TOOL = "alcohol_testing_tool"
