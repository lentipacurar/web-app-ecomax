function onSignIn(googleUser) {
    var id_token = googleUser.getAuthResponse().id_token;
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/google-auth');
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onload = function() {
        console.log('Signed in as: ' + xhr.responseText);
        window.location.replace("/upload");
    };
    xhr.send('idtoken=' + id_token);
}

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const spinner = document.getElementById('spinner');
    const extractedData = document.getElementById('extracted-data-form');
    const templateCheckboxes = document.getElementById('template-checkboxes');
    // default to current date  
    const today = new Date();
    const yyyy = today.getFullYear();
    let mm = today.getMonth() + 1; // Months start at 0!
    let dd = today.getDate();

    if (dd < 10) dd = '0' + dd;
    if (mm < 10) mm = '0' + mm;

    const formattedToday = dd + '/' + mm + '/' + yyyy;

    document.getElementById('data_factura').value = formattedToday;

    fetch('/get-templates')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                populateTemplateCheckboxes(data.templates);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while fetching templates.' + error);
        });

    function populateTemplateCheckboxes(templates) {
        templates.forEach(template => {
            const div = document.createElement('div');
            div.classList.add('form-group');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.name = 'templates';
            checkbox.value = template;
            checkbox.checked = true; // Check by default
            const label = document.createElement('label');
            label.appendChild(document.createTextNode(template));
            div.appendChild(checkbox);
            div.appendChild(label);
            templateCheckboxes.appendChild(div);
        });
    }
    
    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(uploadForm);
        spinner.style.display = 'block';

        fetch('/process-upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            spinner.style.display = 'none';
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                fillDataForm(data);
            }
        })
        .catch(error => {
            spinner.style.display = 'none';
            alert('An error occurred while uploading and processing the file.');
        });
    });

    function getExtractedFormData(data) {
        data.append('nume', document.getElementById('name').value || '');
        data.append('prenume', document.getElementById('surname').value || '');
        data.append('adresa', document.getElementById('address').value || '');
        data.append('cnp', document.getElementById('personal-id').value || '');
        data.append('numar_ci', document.getElementById('document-id').value || '');
        data.append('data_nasterii', document.getElementById('dob').value || '');
        data.append('locul_nasterii', document.getElementById('pob').value || '');
        data.append('data_eliberarii', document.getElementById('doi').value || '');
        data.append('data_expirarii', document.getElementById('doe').value || '');
        const templates = Array.from(document.querySelectorAll('input[name="templates"]:checked'))
                               .map(cb => cb.value);
        data.append('templates', templates);
        var today = new Date();
        var dd = String(today.getDate()).padStart(2, '0');
        var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        var yyyy = today.getFullYear();

        today = dd + '/' + mm + '/' + yyyy;
        data.append('data_curenta', today);
        data.append('asigurator', document.getElementById('listaAsiguratori').value || '');
        data.append('nr_inmatriculare', document.getElementById('nr_auto').value || '');
        data.append('marca_auto', document.getElementById('listaMarciAuto').value || '');
        data.append('nr_contract', document.getElementById('nr_contract').value || '');
        data.append('cuantum', document.getElementById('cuantum').value || '');
        data.append('nr_factura', document.getElementById('nr_factura').value || '');
        data.append('data_factura', document.getElementById('data_factura').value || '');
        data.append('dosar_dauna', document.getElementById('dosar_dauna').value || '');
        data.append('email', document.getElementById('email').value || 'contact@ecomaxprocars.ro');
    }

    function fillDataForm(data) {
        document.getElementById('name').value = data.last_name || '';
        document.getElementById('surname').value = data.first_name || '';
        document.getElementById('address').value = data.address_content || '';
        document.getElementById('personal-id').value = data.personal_number || '';
        document.getElementById('document-id').value = data.document_number_content || '';
        document.getElementById('dob').value = data.dob_content || '';
        document.getElementById('pob').value = data.pob || '';
        document.getElementById('doi').value = data.doi_content || '';
        document.getElementById('doe').value = data.doe_content || '';
    }

    extractedData.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData();
        getExtractedFormData(formData); 
        
        const spinner2 = document.getElementById('spinner2');
        spinner2.style.display = 'block';

        fetch('/generate-docs', {
            method: 'POST',
            body: formData
        })
        .then(async response => {
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.message);
            }
            return response.json();
        })
        .then(data => {
            spinner2.style.display = 'none';
            document.getElementById('generate_result').value = data.message + '\nLista fisierelor generate:\n' + data.files;
        })
        .catch(error => {
            spinner2.style.display = 'none';
            document.getElementById('generate_result').value = 'Error: ' + error.message;
        });
    });
});
