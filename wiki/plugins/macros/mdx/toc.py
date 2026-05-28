from markdown.extensions.toc import TocExtension, TocTreeprocessor, slugify

from wiki.plugins.macros import settings

HEADER_ID_PREFIX = "wiki-toc-"


def process_toc_depth(toc_depth):
    if isinstance(toc_depth, str) and "-" in toc_depth:
        toc_top, toc_bottom = (int(x) for x in toc_depth.split("-"))
    else:
        toc_top = 1
        toc_bottom = int(toc_depth)
    return {"toc_top": toc_top, "toc_bottom": toc_bottom}


def process_bool_value(bool_val, org_val):
    if bool_val.lower() == "false" or bool_val == "0":
        return False
    if bool_val.lower() == "true" or bool_val == "1":
        return True
    return org_val


def process_value(org_val, new_val):
    try:
        if isinstance(new_val, str):
            new_val = new_val.lstrip("'").rstrip("'")

        if isinstance(org_val, bool):
            return process_bool_value(new_val, org_val)
        if isinstance(org_val, int):
            return int(new_val)
        if isinstance(org_val, str):
            return new_val
        return org_val
    except Exception:
        return org_val


def wiki_slugify(*args, **kwargs):
    return HEADER_ID_PREFIX + slugify(*args, **kwargs)


class WikiTreeProcessorClass(TocTreeprocessor):
    CACHED_KWARGS = {}  # Used to cache arguments parsed by the MacroPattern
    # Used to map the keyword arguments to the Class Objects attribute name.
    TOC_CONFIG_VALUES = {
        "title": "title",
        "baselevel": "base_level",
        "separator": "sep",
        "anchorlink": "use_anchors",
        "anchorlink_class": "anchorlink_class",
        "permalink": "use_permalinks",
        "permalink_class": "permalink_class",
        "permalink_title": "permalink_title",
        "toc_class": "toc_class",
        "toc_depth": process_toc_depth,
        "toc_top": "toc_top",
        "toc_bottom": "toc_bottom",
    }

    def run(self, doc):
        # Necessary because self.title is set to a LazyObject via gettext_lazy
        if self.title:
            self.title = str(self.title)

        tmp_kwargs = {}

        def _helper_swap_values(key, value):
            # Saves the existing attribute value to a dictionary
            tmp_kwargs[WikiTreeProcessorClass.TOC_CONFIG_VALUES[key]] = getattr(
                self, WikiTreeProcessorClass.TOC_CONFIG_VALUES[key]
            )
            # This sets the value to a TocTreeprocessor attribute of its corresponding name
            setattr(
                self,
                WikiTreeProcessorClass.TOC_CONFIG_VALUES[key],
                process_value(
                    tmp_kwargs[WikiTreeProcessorClass.TOC_CONFIG_VALUES[key]],
                    value,
                ),
            )

        try:
            # Iterate through CACHED_KWARGS to set attribute values and save defaults to tmp_kwargs
            for k, v in WikiTreeProcessorClass.CACHED_KWARGS.items():
                if (
                    k in WikiTreeProcessorClass.TOC_CONFIG_VALUES
                ):  # Map of keyword names to their respected object attribute names
                    if callable(
                        WikiTreeProcessorClass.TOC_CONFIG_VALUES[k]
                    ):  # Some values in the dictionary are functions to further process values
                        for (
                            tock,
                            tocv,
                        ) in WikiTreeProcessorClass.TOC_CONFIG_VALUES[k](v).items():
                            _helper_swap_values(tock, tocv)
                    else:
                        _helper_swap_values(k, v)
            super().run(doc)
        finally:
            # Use tmp to reset values
            for k, v in tmp_kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            # Unset cached kwargs
            WikiTreeProcessorClass.CACHED_KWARGS = {}


class WikiTocExtension(TocExtension):
    TreeProcessorClass = WikiTreeProcessorClass

    def __init__(self, **kwargs):
        kwargs.setdefault("slugify", wiki_slugify)
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        if "toc" in settings.METHODS:
            TocExtension.extendMarkdown(self, md)


def makeExtension(*args, **kwargs):
    """Return an instance of the extension."""
    return WikiTocExtension(*args, **kwargs)
