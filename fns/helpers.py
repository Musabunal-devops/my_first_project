"""Helper / utility functions."""


def allowed_file(filename, allowed_extensions):
    """
    Check if a file's extension is in the list of allowed extensions.

    Parameters
    ----------
    filename : str
        The name of the file to check.
    allowed_extensions : set
        Set of allowed file extensions (e.g. {"pdf", "doc", "docx"}).

    Returns
    -------
    bool
        Returns True if the file extension is allowed, False otherwise.
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )
