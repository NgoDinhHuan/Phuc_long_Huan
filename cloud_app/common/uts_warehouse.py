from .enum import WarehouseLabelName


def is_forklift_vehicle(class_name: str):
    return class_name.lower() in [
        WarehouseLabelName.FORKLIFT.value,
        WarehouseLabelName.PALLET_TRUCK.value,
        WarehouseLabelName.LOAD_CARRIER.value,
        WarehouseLabelName.ELECTRIC_PALLET_JACK.value,
        WarehouseLabelName.REACH_TRUCK.value,
        WarehouseLabelName.HAND_PALLET_JACK.value,
    ]


def is_person(class_name: str):
    return class_name.lower() in [
        WarehouseLabelName.PERSON.value,
        WarehouseLabelName.PERSON_VISIBLE_CLOTHES.value,
        WarehouseLabelName.PERSON_USE_PHONE.value,
        WarehouseLabelName.PERSON_EAT_DRINK.value,
        WarehouseLabelName.PERSON_CARRY_OBJECT.value,
        # WarehouseLabelName.SECURITY_PERSON.value,
    ]


def is_person_wear_visible_clothes(class_name: str):
    return class_name.lower() in [
        WarehouseLabelName.PERSON_VISIBLE_CLOTHES.value
    ]


def is_person_use_phone(class_name: str):
    return class_name.lower() in [WarehouseLabelName.PERSON_USE_PHONE.value]


def is_person_eat_or_drink(class_name: str):
    return class_name.lower() in [WarehouseLabelName.PERSON_EAT_DRINK.value]


def is_person_carry_object(class_name: str):
    return class_name.lower() in [WarehouseLabelName.PERSON_CARRY_OBJECT.value]


def is_security_person(class_name: str):
    return class_name.lower() in [WarehouseLabelName.SECURITY_PERSON.value]


def is_alcohol_tool(class_name: str):
    return class_name.lower() in [WarehouseLabelName.ALCOHOL_TOOL.value]


def is_face(class_name: str):
    return class_name.lower() in [WarehouseLabelName.FACE.value]


def is_pallet(class_name: str):
    return class_name.lower() in [WarehouseLabelName.PALLET.value]


def is_truck(class_name: str):
    return class_name.lower() in [WarehouseLabelName.TRUCK.value]


def is_product(class_name: str):
    return class_name.lower() in [
        WarehouseLabelName.PRODUCT_BOX.value,
        WarehouseLabelName.PALLET_PACKAGE.value,
        # WarehouseLabelName.PALLET_WITH_BOX.value,
        WarehouseLabelName.PRODUCT_PACKAGE.value,
    ]
