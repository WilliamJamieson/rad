from datamodel_code_generator.imports import Import

from ._adaptor_tags import asdf_tags


def has_adaptor(obj) -> bool:
    return obj.tag in asdf_tags


def _ndarray_factory(obj, import_):
    extras = obj.extras

    dtype = extras.get("datatype", None)
    if dtype is not None:
        dtype = f"np.{dtype}"
        import_ += ", np"

    return f"{dtype}, {extras.get('ndim', None)}", import_


def _unit_factory(unit, import_):
    if unit is not None and unit.enum is not None:
        import_ += ", Unit"

        units = [f'Unit("{u}")' for u in unit.enum]

        if len(units) == 1:
            unit = units[0]
        else:
            unit = f"({', '.join(units)})"

    return unit, import_


def adaptor_factory(obj, _context):
    ctx = _context.copy()

    if obj.tag == asdf_tags.ASTROPY_TIME:
        ctx.type = "AstropyTime"
        ctx.import_ = Import(from_="rad.pydantic.adaptors", import_="AstropyTime")

        return ctx

    if obj.tag == asdf_tags.ASDF_NDARRAY:
        type_, import_ = _ndarray_factory(obj, "NdArray")

        ctx.type = f"NdArray[{type_}]"
        ctx.import_ = Import(from_="rad.pydantic.adaptors", import_=import_)

        return ctx

    if obj.tag == asdf_tags.ASTROPY_UNIT:
        type_, import_ = _unit_factory(obj, "AstropyUnit")

        ctx.type = f"AstropyUnit[{type_}]"
        ctx.import_ = Import(from_="rad.pydantic.adaptors", import_=import_)

        return ctx

    if obj.tag == asdf_tags.ASTROPY_QUANTITY:
        properties = obj.properties
        import_ = "AstropyQuantity"

        if "datatype" in properties:
            import_ += ", np"
            value = f"np.{properties['datatype'].enum[0]}, 0"
        else:
            value = properties.get("value", None)
            if value is not None:
                value, import_ = _ndarray_factory(value, import_)

        unit = properties.get("unit", None)
        unit, import_ = _unit_factory(unit, import_)

        ctx.type = f"AstropyQuantity[{value}, {unit}]"
        ctx.import_ = Import(from_="rad.pydantic.adaptors", import_=import_)

        return ctx

    raise NotImplementedError(f"Unsupported tag: {obj.tag}")
