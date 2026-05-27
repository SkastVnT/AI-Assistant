const CAT = '[mySlider]';

export function setupSlider(containerId, spanText = 'mySlider', min = 0, max = 255, step = 1, defaultValue = 0, callback = null) {
    const container = document.querySelector(`.${containerId}`);
    if (!container) {
        console.error(CAT, `[setupSlider] Container with class "${containerId}" not found.`);
        return;
    }

    container.innerHTML = `        
        <div class="mySlider-${containerId}-row">
            <span class="mySlider-${containerId}-span">${spanText}</span>
            <input class="mySlider-${containerId}-value" type="number" min="${min}" max="${max}" step="${step}" value="${defaultValue}">
        </div>
        <input class="mySlider-${containerId}-bar" type="range" min="${min}" max="${max}" step="${step}" value="${defaultValue}">
    `;

    const sliderBar = container.querySelector(`.mySlider-${containerId}-bar`);
    const sliderText = container.querySelector(`.mySlider-${containerId}-value`);
    const sliderSpan = container.querySelector(`.mySlider-${containerId}-span`);

    // Determine if the value should be treated as an integer based on step
    const isIntegerStep = Number.isInteger(step);

    const getTypedValue = (value) => {
        const parsed = Number.parseFloat(value);
        return isIntegerStep ? Number.parseInt(parsed, 10) : parsed;
    };

    sliderBar.addEventListener('input', () => {
        sliderText.value = sliderBar.value;
        if (callback) {
            callback(getTypedValue(sliderBar.value));
        }
    });

    sliderText.addEventListener('input', () => {
        const value = Number.parseFloat(sliderText.value);

        if (value >= min && value <= max) {
            sliderBar.value = value;
            if (callback) {
                callback(getTypedValue(value));
            }
        } else {
            console.warn(CAT, '[setupSlider] Value out of range:', value);
        }
    });

    return {
        setValue: (value) => {
            if (value >= min && value <= max) {
                sliderBar.value = value;
                sliderText.value = value;
                if (callback) {
                    callback(getTypedValue(value));
                }
            } else {
                console.warn(CAT, '[setValue] Value out of range.');
            }
        },
        getValue: () => {
            return Number.parseInt(sliderBar.value, 10);
        },
        getFloat: () => {
            return Number.parseFloat(sliderBar.value);
        },
        setTitle: (text) => {
            sliderSpan.textContent = text;
        }
    };
}