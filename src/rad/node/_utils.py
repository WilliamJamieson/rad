def name_from_uri(uri: str) -> str:
    """
    Compute the name of the schema from the uri

    Parameters
    ----------
    uri : str
        The uri to use to find the name from
    """
    tag_uri_split = uri.split("/")[-1].split("-")[0]
    if "/tvac/" in uri and "tvac" not in tag_uri_split:
        tag_uri_split = "tvac_" + uri.split("/")[-1].split("-")[0]
    elif "/fps/" in uri and "fps" not in tag_uri_split:
        tag_uri_split = "fps_" + uri.split("/")[-1].split("-")[0]
    return tag_uri_split
