/**
 * Templates definitions for photo booth layouts
 */

// Template definitions
const templates = {
    classic: {
        name: 'Classic',
        class: 'classic-template',
        backgroundColor: '#ffffff',
        borderColor: '#000000',
        textColor: '#000000',
        padding: '20px',
        border: '5px solid black'
    },
    modern: {
        name: 'Modern',
        class: 'modern-template',
        backgroundColor: '#333333',
        borderColor: '#666666',
        textColor: '#ffffff',
        padding: '15px',
        border: 'none',
        borderRadius: '15px'
    },
    vintage: {
        name: 'Vintage',
        class: 'vintage-template',
        backgroundColor: '#f9e4c3',
        borderColor: '#8b4513',
        textColor: '#8b4513',
        padding: '20px',
        border: '10px solid #8b4513'
    }
};

/**
 * Get a template by its id
 * @param {string} templateId - The id of the template to retrieve
 * @returns {Object} The template object
 */
function getTemplate(templateId) {
    return templates[templateId] || templates.classic;
}

/**
 * Apply template styles to a photo strip element
 * @param {HTMLElement} element - The element to style
 * @param {string} templateId - The id of the template to apply
 */
function applyTemplate(element, templateId) {
    const template = getTemplate(templateId);
    
    // Remove all template classes first
    Object.values(templates).forEach(t => {
        element.classList.remove(t.class);
    });
    
    // Add the specific template class
    element.classList.add(template.class);
    
    // Apply inline styles
    element.style.backgroundColor = template.backgroundColor;
    element.style.border = template.border;
    element.style.borderRadius = template.borderRadius || '0';
    element.style.padding = template.padding;
}
