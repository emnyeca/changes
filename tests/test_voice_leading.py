from harmony_cloud.voice_leading import generate_voice_leading


def test_generate_voice_leading_placeholder():
    # Create two triads and ensure the function returns a list
    voicings = generate_voice_leading([[60, 64, 67], [62, 65, 69]])
    assert isinstance(voicings, list)
