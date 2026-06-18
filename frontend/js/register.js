// ==========================================
// 1. DOM ELEMENTS
// ==========================================
const registerForm = document.getElementById('registrationForm');
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirmPassword');
const errorText = document.getElementById('passwordError');
const passwordRulesText = document.getElementById('passwordRules');
const phoneInput = document.getElementById('phone');
const allRequiredInputs = document.querySelectorAll('input[required], select[required]');

const togglePasswordBtn = document.getElementById('togglePassword');
const eyeIconPassword = document.getElementById('eyeIconPassword');
const toggleConfirmBtn = document.getElementById('toggleConfirmPassword');
const eyeIconConfirm = document.getElementById('eyeIconConfirm');


// ==========================================
// 2. SHOW/HIDE PASSWORD LOGIC
// ==========================================
const eyeSlashPath = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />`;
const eyeOpenPath = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />`;

function toggleVisibility(inputElement, iconElement) {
    if (inputElement.type === 'password') {
        inputElement.type = 'text';
        iconElement.innerHTML = eyeSlashPath;
    } else {
        inputElement.type = 'password';
        iconElement.innerHTML = eyeOpenPath;
    }
}

togglePasswordBtn.addEventListener('click', () => toggleVisibility(passwordInput, eyeIconPassword));
toggleConfirmBtn.addEventListener('click', () => toggleVisibility(confirmPasswordInput, eyeIconConfirm));


// ==========================================
// 3. REAL-TIME UI VALIDATION
// ==========================================

// A. Phone Number: Force numbers only & setup error text
const phoneErrorText = document.createElement('p');
phoneErrorText.className = 'text-red-500 text-xs mt-1 hidden font-medium';
phoneErrorText.textContent = 'Phone number must be exactly 10 digits.';
phoneInput.parentNode.appendChild(phoneErrorText);

phoneInput.addEventListener('input', function() {
    this.value = this.value.replace(/[^0-9]/g, ''); // Remove non-digits instantly
    this.classList.remove('border-red-500', 'focus:ring-red-500');
    phoneErrorText.classList.add('hidden');
});

// B. Empty Field Check ("Must Fill" Warnings)
allRequiredInputs.forEach(input => {
    const requiredWarning = document.createElement('p');
    requiredWarning.className = 'text-red-500 text-xs mt-1 hidden font-medium';
    requiredWarning.textContent = 'This field is required.';
    
    if(input.id !== 'confirmPassword') {
        input.parentNode.appendChild(requiredWarning);
    }

    input.addEventListener('blur', function() {
        if (!this.value.trim()) {
            this.classList.add('border-red-500', 'focus:ring-red-500');
            this.classList.remove('border-border', 'focus:ring-primary');
            if(input.id !== 'confirmPassword') requiredWarning.classList.remove('hidden');
            if (this.id === 'password') passwordRulesText.classList.add('hidden');
        }
    });

    input.addEventListener('input', function() {
        if (this.value.trim()) {
            this.classList.remove('border-red-500', 'focus:ring-red-500');
            this.classList.add('border-border', 'focus:ring-primary');
            if(input.id !== 'confirmPassword') requiredWarning.classList.add('hidden');
        }
    });
});

// C. Password Rules Visibility
passwordInput.addEventListener('focus', function() {
    passwordRulesText.classList.remove('hidden');
});

passwordInput.addEventListener('input', function() {
    passwordRulesText.classList.replace('text-red-500', 'text-text-muted');
    passwordRulesText.classList.remove('font-bold');
});

confirmPasswordInput.addEventListener('input', function() {
    errorText.classList.add('hidden');
    this.classList.remove('border-red-500', 'focus:ring-red-500');
    this.classList.add('border-border', 'focus:ring-primary');
});


// ==========================================
// 4. FORM SUBMISSION & BACKEND CONNECTION
// ==========================================
registerForm.addEventListener('submit', function(event) {
    // Stop the page from reloading
    event.preventDefault(); 
    let formIsValid = true;

    // A. Final Validations before sending
    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,13}$/;

    if (!strongPasswordRegex.test(passwordInput.value)) {
        passwordInput.classList.add('border-red-500', 'focus:ring-red-500');
        passwordRulesText.classList.replace('text-text-muted', 'text-red-500');
        passwordRulesText.classList.add('font-bold');
        passwordRulesText.classList.remove('hidden');
        formIsValid = false;
    }

    if (passwordInput.value !== confirmPasswordInput.value) {
        errorText.classList.remove('hidden');
        confirmPasswordInput.classList.add('border-red-500', 'focus:ring-red-500');
        formIsValid = false;
    }

    if (phoneInput.value.length !== 10) {
        phoneInput.classList.add('border-red-500', 'focus:ring-red-500');
        phoneErrorText.classList.remove('hidden');
        formIsValid = false;
    }

    // B. Package and Send to Django
    if (formIsValid) {
        // Build the JSON object mapping to Django's expected fields
        const userData = {
            fullName: document.getElementById('fullName').value,
            email: document.getElementById('email').value,
            phone: phoneInput.value,
            role: document.getElementById('role').value,
            password: passwordInput.value
        };
            console.log("Data", userData);
        // Send the HTTP POST request
        fetch('http://127.0.0.1:8000/api/auth/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        })
        .then(response => {
            if (response.ok) {
                alert("Account created successfully!");
                window.location.href = "login.html"; // Redirect to login
            } else {
                response.json().then(data => {
                    console.error("Backend Validation Error:", data);
                    // Check if Django sent back a specific email error
                    if(data.email) {
                        alert("Error: " + data.email[0]);
                    } else {
                        alert("Registration failed. Please check your details.");
                    }
                });
            }
        })
        .catch(error => {
            console.error("Network Error:", error);
            alert("Could not connect to the server. Is Django running?");
        });
    }
});             