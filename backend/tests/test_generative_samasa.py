import pytest
from app.services.samasa import get_samasa_service

@pytest.fixture(scope="module")
def samasa_svc():
    return get_samasa_service()

def test_unseen_avyayibhava_compounds(samasa_svc):
    """Verifies that arbitrary unseen Avyayībhāva compounds decompose dynamically."""
    # यथा + देश -> देशम् अनतिक्रम्य
    res1 = samasa_svc.analyze_compound("यथादेशम्")
    assert res1 is not None
    assert res1.samasa_type == "अव्ययीभावः"
    assert "देश" in res1.vigraha_vakya
    assert "अनतिक्रम्य" in res1.vigraha_vakya

    # उप + विद्यालय -> विद्यालयस्य समीपम्
    res2 = samasa_svc.analyze_compound("उपविद्यालयम्")
    assert res2 is not None
    assert res2.samasa_type == "अव्ययीभावः"
    assert "विद्यालयस्य समीपम्" in res2.vigraha_vakya

    # स + स्मित -> स्मितेन सहितम्
    res3 = samasa_svc.analyze_compound("सस्मितम्")
    assert res3 is not None
    assert res3.samasa_type == "अव्ययीभावः"
    assert "स्मितेन सहितम्" in res3.vigraha_vakya

def test_unseen_tatpurusha_compounds(samasa_svc):
    """Verifies that arbitrary unseen Tatpuruṣa compounds decompose with correct case inflection."""
    # व्याघ्र + भीतः -> व्याघ्रात् भीतः (पञ्चमी-तत्पुरुषः)
    res_panchami = samasa_svc.analyze_compound("व्याघ्रभीतः")
    assert res_panchami is not None
    assert "पञ्चमी-तत्पुरुषः" in res_panchami.samasa_type
    assert "व्याघ्रात्" in res_panchami.vigraha_vakya

    # ज्ञान + वृद्धः -> ज्ञानेन वृद्धः (तृतीया-तत्पुरुषः)
    res_tritiya = samasa_svc.analyze_compound("ज्ञानवृद्धः")
    assert res_tritiya is not None
    assert "तृतीया-तत्पुरुषः" in res_tritiya.samasa_type
    assert "ज्ञानेन" in res_tritiya.vigraha_vakya

    # शास्त्र + पण्डितः -> शास्त्रे पण्डितः (सप्तमी-तत्पुरुषः)
    res_saptami = samasa_svc.analyze_compound("शास्त्रपण्डितः")
    assert res_saptami is not None
    assert "सप्तमी-तत्पुरुषः" in res_saptami.samasa_type
    assert "शास्त्रे" in res_saptami.vigraha_vakya

    # सूर्य + प्रकाशः -> सूर्यस्य प्रकाशः (षष्ठी-तत्पुरुषः)
    res_shashthi = samasa_svc.analyze_compound("सूर्यप्रकाशः")
    assert res_shashthi is not None
    assert "षष्ठी-तत्पुरुषः" in res_shashthi.samasa_type
    assert "सूर्यस्य" in res_shashthi.vigraha_vakya

def test_unseen_dvandva_and_karmadharaya(samasa_svc):
    """Verifies that arbitrary unseen Dvandva and Karmadhāraya compounds decompose dynamically."""
    # मृग + काकौ -> मृगः च काकः च
    res_dvandva = samasa_svc.analyze_compound("मृगकाकौ")
    assert res_dvandva is not None
    assert "द्वन्द्वः" in res_dvandva.samasa_type
    assert "च" in res_dvandva.vigraha_vakya

    # कृष्ण + सर्पः -> कृष्णः चासौ सर्पः (कर्मधारयः)
    res_karma = samasa_svc.analyze_compound("कृष्णसर्पः")
    assert res_karma is not None
    assert "कर्मधारयः" in res_karma.samasa_type
    assert "कृष्ण" in res_karma.vigraha_vakya
