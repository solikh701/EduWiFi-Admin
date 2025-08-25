document.getElementById('loginForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const login = document.getElementById('login').value;
    const password = document.getElementById('password').value;

    fetch('/api/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            login: login,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const login = 'userLoginData';
            const expirationTime = new Date().getTime() + (12 * 60 * 60 * 1000);

            localStorage.setItem('loggedInUser', login);
            localStorage.setItem('loginExpiration', expirationTime);

            window.location.href = '/admin_panel_main';
        } else {
            alert("Login yoki parol noto'g'ri. Iltimos, qayta urinib ko'ring.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Server bilan bog'lanishda xatolik yuz berdi.");
    });
});

document.getElementById('togglePassword').addEventListener('click', function () {
    const passwordField = document.getElementById('password');
    const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordField.setAttribute('type', type);
    this.textContent = type === 'password' ? '👁️' : '🙈';
});
