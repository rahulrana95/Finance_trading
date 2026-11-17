"""Every address outside /api serves the built interface."""

from pathlib import Path

from tests.conftest import INDEX_BODY, ClientFactory


def test_root_serves_the_interface(make_client: ClientFactory, static_dir: Path):
    response = make_client(static_dir).get("/")
    assert response.status_code == 200
    assert response.text == INDEX_BODY


def test_page_addresses_load_the_app(make_client: ClientFactory, static_dir: Path):
    # The single-page app owns its addresses, so reloading /trades must still load it.
    client = make_client(static_dir)
    for path in ("/trades", "/stocks/NESTLEIND", "/sign-in"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.text == INDEX_BODY


def test_built_files_are_served(make_client: ClientFactory, static_dir: Path):
    client = make_client(static_dir)
    assert client.get("/assets/app.js").text.startswith("console.log('app')")
    assert client.get("/favicon.svg").text == "<svg/>"


def test_large_files_are_compressed(make_client: ClientFactory, static_dir: Path):
    response = make_client(static_dir).get("/assets/app.js", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"


def test_a_missing_file_is_404_not_the_app(make_client: ClientFactory, static_dir: Path):
    assert make_client(static_dir).get("/assets/missing.js").status_code == 404


def test_a_path_cannot_escape_the_interface_folder(make_client: ClientFactory, static_dir: Path):
    client = make_client(static_dir)
    for path in ("/..%2Fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2F..%2Fsecret.txt"):
        assert "do not serve" not in client.get(path).text


def test_writing_to_the_interface_is_refused(make_client: ClientFactory, static_dir: Path):
    assert make_client(static_dir).post("/trades").status_code == 405


def test_without_a_built_interface_pages_are_404(make_client: ClientFactory):
    response = make_client(None).get("/trades")
    assert response.status_code == 404
    assert response.json() == {"detail": "Interface is not built"}
