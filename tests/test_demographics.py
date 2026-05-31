from src.demographics import profile_for, grupo_etario, party_weights, approval_weights, PARTIES


def test_profile_es_deterministico():
    assert profile_for("person_00018") == profile_for("person_00018")


def test_profile_tiene_campos_y_rangos():
    p = profile_for("person_01234")
    assert set(p) == {"respondent_id", "edad", "grupo_etario", "region", "nse", "genero"}
    assert 16 <= p["edad"] <= 90
    assert p["region"] in {"AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"}
    assert p["nse"] in {"alto", "medio", "bajo"}
    assert p["genero"] in {"F", "M", "X"}


def test_grupo_etario_bordes():
    assert grupo_etario(16) == "16-29"
    assert grupo_etario(29) == "16-29"
    assert grupo_etario(30) == "30-44"
    assert grupo_etario(64) == "45-64"
    assert grupo_etario(65) == "65+"


def test_party_weights_largo_y_positivos():
    w = party_weights("AMBA", "bajo")
    assert len(w) == len(PARTIES) == 5 and all(x > 0 for x in w)


def test_party_weights_correlacion():
    idx = PARTIES.index("Union Republicana")
    assert party_weights("Centro", "alto")[idx] > party_weights("Centro", "bajo")[idx]


def test_approval_weights_correlacion():
    assert approval_weights("alto")[0] > approval_weights("bajo")[0]
