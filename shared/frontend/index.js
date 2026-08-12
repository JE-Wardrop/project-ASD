// Wait for the DOM structure to fully load
document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('actionBtn');
    const message = document.getElementById('message');

    // Add click event listener to the button
    button.addEventListener('click', () => {
        // Toggle the visibility of the success message
        if (message.classList.contains('hidden')) {
            message.classList.remove('hidden');
            button.textContent = 'Hide Message';
        } else {
            message.classList.add('hidden');
            button.textContent = 'Click Me!';
        }
    });
});
