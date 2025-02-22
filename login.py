import requests


def login():
    """Belirtilen kullanıcı ile giriş yapar ve token döndürür."""
    url = "http://www.dgnonline.com/rest1/auth/login/selim.sarikaya"
    data = {'pass': 'Talipsan.4244'}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()  # Hata olup olmadığını kontrol et

    result = response.json()
    if result.get('success'):
        token = result['data'][0]['token']
        return token

    raise Exception("❌ Giriş başarısız: " + str(result))