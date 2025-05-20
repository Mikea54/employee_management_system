from utils.helpers import allowed_file


def test_allowed_file_uppercase_pdf():
    assert allowed_file("report.PDF") is True


def test_allowed_file_zip_not_allowed():
    assert allowed_file("archive.zip") is False


def test_allowed_file_docx_allowed():
    assert allowed_file("document.docx") is True
