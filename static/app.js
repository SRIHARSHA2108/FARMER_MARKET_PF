(function () {
    function getLanguage() {
        return localStorage.getItem("farmerMarketLanguage") || "en";
    }

    function getLanguageModule(language) {
        return window.FARMER_MARKET_LANGUAGES[language] || window.FARMER_MARKET_LANGUAGES.en;
    }

    function setLanguage(language) {
        const languageModule = getLanguageModule(language);
        const dictionary = languageModule.translations;
        document.documentElement.lang = language;
        document.querySelectorAll("[data-i18n]").forEach((element) => {
            const key = element.getAttribute("data-i18n");
            if (dictionary[key]) {
                element.textContent = dictionary[key];
            }
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
            const key = element.getAttribute("data-i18n-placeholder");
            if (dictionary[key]) {
                element.setAttribute("placeholder", dictionary[key]);
            }
        });
        document.querySelectorAll("[data-crop-name]").forEach((element) => {
            const originalName = element.getAttribute("data-crop-name");
            element.textContent = languageModule.translateCropName(originalName);
        });
        document.querySelectorAll("[data-slice-label]").forEach((element) => {
            const originalLabel = element.getAttribute("data-slice-label");
            element.textContent = languageModule.sliceLabels[originalLabel] || originalLabel;
        });
        document.querySelectorAll("[data-season-name]").forEach((element) => {
            const originalSeason = element.textContent.trim();
            element.setAttribute("data-season-original", element.getAttribute("data-season-original") || originalSeason);
            const season = element.getAttribute("data-season-original");
            element.textContent = languageModule.seasonNames[season] || season;
        });
        document.querySelectorAll("[data-season-note]").forEach((element) => {
            const season = element.getAttribute("data-season-note");
            element.textContent = languageModule.seasonNotes[season] || element.textContent;
        });
        document.querySelectorAll("[data-direction]").forEach((element) => {
            const direction = element.getAttribute("data-direction");
            element.textContent = languageModule.directionLabels[direction] || direction;
        });
        document.querySelectorAll("[data-lang-button]").forEach((button) => {
            button.classList.toggle("active", button.getAttribute("data-lang-button") === language);
        });
        localStorage.setItem("farmerMarketLanguage", language);
    }

    function buildSpeechContext(languageModule) {
        const seasonTitle = document.querySelector(".season-panel h3")?.textContent.trim() || "";
        const weather = document.querySelector(".weather-card strong")?.textContent.trim() || "";
        const cropLines = Array.from(document.querySelectorAll(".crop-card")).slice(0, 5).map((card) => {
            const cropElement = card.querySelector("[data-crop-name]");
            const crop = languageModule.translateCropName(cropElement?.getAttribute("data-crop-name") || cropElement?.textContent.trim() || "");
            const price = card.querySelector(".crop-card-head strong")?.textContent.trim() || "";
            const forecast = card.querySelector(".crop-stats div:nth-child(3) strong")?.textContent.trim() || "";
            return languageModule.buildCropSpeech(crop, price, forecast);
        });
        return { seasonTitle, weather, cropLines };
    }

    function speakPage() {
        if (!("speechSynthesis" in window)) {
            alert("Speech is not supported in this browser.");
            return;
        }
        const language = getLanguage();
        const languageModule = getLanguageModule(language);
        const utterance = new SpeechSynthesisUtterance(
            languageModule.buildSpeechText(buildSpeechContext(languageModule))
        );
        utterance.lang = languageModule.speechCode;
        utterance.rate = 0.9;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    function stopSpeech() {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        setLanguage(getLanguage());
        document.querySelectorAll("[data-lang-button]").forEach((button) => {
            button.addEventListener("click", () => setLanguage(button.getAttribute("data-lang-button")));
        });
        document.querySelectorAll("[data-speak-page]").forEach((button) => {
            button.addEventListener("click", speakPage);
        });
        document.querySelectorAll("[data-stop-speech]").forEach((button) => {
            button.addEventListener("click", stopSpeech);
        });
    });
})();
