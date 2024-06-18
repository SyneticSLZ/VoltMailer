document.getElementById('openPopup').addEventListener('click', () => {
    document.getElementById('popup').classList.remove('hidden');
});

document.getElementById('closePopup').addEventListener('click', () => {
    document.getElementById('popup').classList.add('hidden');
});

document.getElementById('profileTab').addEventListener('click', () => {
    showContent('profileContent');
});

document.getElementById('workspacesTab').addEventListener('click', () => {
    showContent('workspacesContent');
});

document.getElementById('sessionsTab').addEventListener('click', () => {
    showContent('sessionsContent');
});

function showContent(contentId) {
    const contents = document.querySelectorAll('.content');
    contents.forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(contentId).classList.add('active');

    const tabs = document.querySelectorAll('.sidebar-item');
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`#${contentId}Tab`).classList.add('active');
}

// Function to handle tab switching
function switchTab(event) {
    // Remove active class from all menu items
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => item.classList.remove('active'));

    // Add active class to the clicked menu item
    event.currentTarget.classList.add('active');

    // Get the content div
    const contentDiv = document.querySelector('.content');

    // Clear current content
    contentDiv.innerHTML = '';

    // Get the id of the clicked menu item
    const id = event.currentTarget.id;

    // Switch content based on the clicked menu item
    switch (id) {
        case '1':
            contentDiv.innerHTML = '<h2>Home Content</h2><p>This is the home page content.</p>';
            break;
        case '2':
            contentDiv.innerHTML = '<h2>Usage Content</h2><p>This is the usage page content.</p>';
            break;
        case '3':
            contentDiv.innerHTML = '<h2>Billing Content</h2><p>This is the billing page content.</p>';
            break;
        case '4':
            contentDiv.innerHTML = '<h2>Account Content</h2><p>This is the account page content.</p>';
            break;
        case '5':
            contentDiv.innerHTML = '<h2>Help Content</h2><p>This is the help page content.</p>';
            break;
        default:
            contentDiv.innerHTML = '<h2>Home Content</h2><p>This is the default home page content.</p>';
    }
}

// Attach event listeners to menu items
const menuItems = document.querySelectorAll('.menu-item');
menuItems.forEach(item => {
    item.addEventListener('click', switchTab);
});