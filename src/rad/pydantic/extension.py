from asdf.extension import Extension

# Import all the models so they get registered
from . import _generated  # noqa: F401
from .converter import RadDataModelConverter
from .datamodel import RadDataModel

TAGGED_MODELS = {}
for model_name in _generated.__all__:
    model = getattr(_generated, model_name)
    if issubclass(model, RadDataModel) and model._tag_uri is not None:
        TAGGED_MODELS[model._tag_uri] = model

# Add all the models to the converter
RadDataModelConverter.from_registry(TAGGED_MODELS)


class RadPydanticExtension(Extension):
    extension_uri = "asdf://stsci.edu/datamodels/roman/manifests/datamodels-1.0"
    converters = [RadDataModelConverter()]
    tags = list(TAGGED_MODELS.keys())
