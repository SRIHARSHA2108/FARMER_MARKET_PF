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
        document.querySelectorAll("[data-i18n-title]").forEach((element) => {
            const key = element.getAttribute("data-i18n-title");
            if (dictionary[key]) {
                element.setAttribute("title", dictionary[key]);
                element.setAttribute("aria-label", dictionary[key]);
            }
        });
        document.querySelectorAll("[data-search-mic]").forEach((button) => {
            button.textContent = dictionary.mic || "Mic";
        });
        document.querySelectorAll("[data-chat-mic]").forEach((button) => {
            button.textContent = dictionary.mic || "Mic";
        });
        document.querySelectorAll("[data-chat-messages]").forEach((messages) => {
            if (!messages.children.length) {
                addChatMessage(dictionary.chatWelcome, "bot");
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
        filterCrops();
    }

    function getSearchableText(card, languageModule) {
        const names = Array.from(card.querySelectorAll("[data-crop-name]")).map((element) => {
            const originalName = element.getAttribute("data-crop-name") || "";
            return `${originalName} ${languageModule.translateCropName(originalName)}`;
        });
        return `${card.textContent} ${names.join(" ")}`.toLowerCase();
    }

    function filterCrops() {
        const input = document.querySelector("[data-crop-search]");
        if (!input) {
            return;
        }
        const languageModule = getLanguageModule(getLanguage());
        const query = input.value.trim().toLowerCase();
        let visibleCount = 0;
        document.querySelectorAll(".crop-card").forEach((card) => {
            const isMatch = !query || getSearchableText(card, languageModule).includes(query);
            card.hidden = !isMatch;
            if (isMatch) {
                visibleCount += 1;
            }
        });

        const countElement = document.querySelector("[data-search-count]");
        if (countElement) {
            const dictionary = languageModule.translations;
            countElement.textContent = visibleCount
                ? `${visibleCount} ${dictionary.resultsFound}`
                : dictionary.noResults;
        }
    }

    function startSearchMic(button) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const languageModule = getLanguageModule(getLanguage());
        const dictionary = languageModule.translations;
        if (!SpeechRecognition) {
            alert(dictionary.speechNotSupported);
            return;
        }

        const input = document.querySelector("[data-crop-search]");
        if (!input) {
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = languageModule.speechCode;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        button.classList.add("listening");
        button.textContent = dictionary.listening;

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            input.value = transcript;
            filterCrops();
            input.focus();
        };

        recognition.onend = () => {
            button.classList.remove("listening");
            button.textContent = dictionary.mic || "Mic";
        };

        recognition.onerror = () => {
            button.classList.remove("listening");
            button.textContent = dictionary.mic || "Mic";
        };

        recognition.start();
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

    function getCropCardSpeechContext(card, languageModule) {
        const cropElement = card.querySelector("[data-crop-name]");
        const crop = languageModule.translateCropName(cropElement?.getAttribute("data-crop-name") || cropElement?.textContent.trim() || "");
        const price = card.querySelector(".crop-card-head strong")?.textContent.trim() || "";
        const minPrice = card.querySelector(".crop-stats div:nth-child(1) strong")?.textContent.trim() || "";
        const maxPrice = card.querySelector(".crop-stats div:nth-child(2) strong")?.textContent.trim() || "";
        const forecast = card.querySelector(".crop-stats div:nth-child(3) strong")?.textContent.trim() || "";
        const rain = card.querySelector(".signal-row span:nth-child(1)")?.textContent.trim() || "";
        return { crop, price, minPrice, maxPrice, forecast, rain };
    }

    function speakCrop(card) {
        if (!("speechSynthesis" in window)) {
            alert("Speech is not supported in this browser.");
            return;
        }
        const languageModule = getLanguageModule(getLanguage());
        const utterance = new SpeechSynthesisUtterance(
            languageModule.buildSingleCropSpeech(getCropCardSpeechContext(card, languageModule))
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

    function addChatMessage(text, sender) {
        const messages = document.querySelector("[data-chat-messages]");
        if (!messages) {
            return;
        }
        const message = document.createElement("div");
        message.className = `chat-message ${sender}`;
        message.textContent = text;
        messages.appendChild(message);
        messages.scrollTop = messages.scrollHeight;
    }

    function getCropInfoFromCard(card, languageModule) {
        const cropElement = card.querySelector("[data-crop-name]");
        const originalName = cropElement?.getAttribute("data-crop-name") || "";
        return {
            originalName,
            translatedName: languageModule.translateCropName(originalName),
            price: card.querySelector(".crop-card-head strong")?.textContent.trim() || "",
            minPrice: card.querySelector(".crop-stats div:nth-child(1) strong")?.textContent.trim() || "",
            maxPrice: card.querySelector(".crop-stats div:nth-child(2) strong")?.textContent.trim() || "",
            forecast: card.querySelector(".crop-stats div:nth-child(3) strong")?.textContent.trim() || "",
        };
    }

    function buildChatApiContext(languageModule) {
        const crops = Array.from(document.querySelectorAll(".crop-card")).slice(0, 12).map((card) => {
            const info = getCropInfoFromCard(card, languageModule);
            return {
                crop: info.translatedName,
                originalCrop: info.originalName,
                price: info.price,
                minPrice: info.minPrice,
                maxPrice: info.maxPrice,
                forecast: info.forecast,
            };
        });
        return {
            weather: document.querySelector(".weather-card")?.innerText.trim() || "",
            season: document.querySelector(".season-panel")?.innerText.trim() || "",
            crops,
        };
    }

    function answerChat(question) {
        const languageModule = getLanguageModule(getLanguage());
        const responses = languageModule.chatResponses;
        const normalizedQuestion = question.toLowerCase();
        const cards = Array.from(document.querySelectorAll(".crop-card"));

        if (!cards.length) {
            return responses.noDashboard;
        }
        if (normalizedQuestion.includes("help") || normalizedQuestion.includes("ಸಹಾಯ")) {
            return responses.help;
        }
        if (normalizedQuestion.includes("season") || normalizedQuestion.includes("ಋತು")) {
            const seasonText = document.querySelector(".season-panel")?.innerText.trim();
            return seasonText || responses.season;
        }
        if (normalizedQuestion.includes("weather") || normalizedQuestion.includes("rain") || normalizedQuestion.includes("ಹವಾಮಾನ") || normalizedQuestion.includes("ಮಳೆ")) {
            return document.querySelector(".weather-card")?.innerText.trim() || responses.weather;
        }
        if (normalizedQuestion.includes("top") || normalizedQuestion.includes("price") || normalizedQuestion.includes("ಬೆಲೆ") || normalizedQuestion.includes("ಮುಖ್ಯ")) {
            const topPrices = cards.slice(0, 4).map((card) => {
                const info = getCropInfoFromCard(card, languageModule);
                return `${info.translatedName}: ${info.price}`;
            });
            return `${responses.topPrices} ${topPrices.join(", ")}`;
        }

        const matchedCard = cards.find((card) => {
            const info = getCropInfoFromCard(card, languageModule);
            const searchText = `${info.originalName} ${info.translatedName}`.toLowerCase();
            return searchText.split(/\s+/).some((word) => word.length > 2 && normalizedQuestion.includes(word));
        });
        if (!matchedCard) {
            return responses.notFound;
        }

        const info = getCropInfoFromCard(matchedCard, languageModule);
        if (getLanguage() === "kn") {
            return `${info.translatedName}: ಪ್ರಸ್ತುತ ಬೆಲೆ ${info.price}, ಕನಿಷ್ಠ ${info.minPrice}, ಗರಿಷ್ಠ ${info.maxPrice}, 4 ವಾರಗಳ ಮುನ್ಸೂಚನೆ ${info.forecast}.`;
        }
        return `${info.translatedName}: current price ${info.price}, minimum ${info.minPrice}, maximum ${info.maxPrice}, 4 week forecast ${info.forecast}.`;
    }

    function openChatbot() {
        const panel = document.querySelector("[data-chat-panel]");
        if (panel) {
            panel.hidden = false;
            document.querySelector("[data-chat-input]")?.focus();
        }
    }

    function closeChatbot() {
        const panel = document.querySelector("[data-chat-panel]");
        if (panel) {
            panel.hidden = true;
        }
    }

    function speakText(text) {
        if (!("speechSynthesis" in window)) {
            return;
        }
        const languageModule = getLanguageModule(getLanguage());
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = languageModule.speechCode;
        utterance.rate = 0.9;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    async function submitChat(question) {
        const cleanQuestion = question.trim();
        if (!cleanQuestion) {
            return;
        }
        addChatMessage(cleanQuestion, "user");
        const language = getLanguage();
        const languageModule = getLanguageModule(language);
        const dictionary = languageModule.translations;
        let answer = "";

        if (window.fetch) {
            addChatMessage(dictionary.aiThinking, "bot");
            try {
                const response = await fetch("/api/chatbot", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        question: cleanQuestion,
                        language,
                        context: buildChatApiContext(languageModule),
                    }),
                });
                const data = await response.json();
                answer = data.answer || "";
            } catch (error) {
                answer = "";
            }
            const messages = document.querySelector("[data-chat-messages]");
            const lastMessage = messages?.lastElementChild;
            if (lastMessage?.textContent === dictionary.aiThinking) {
                lastMessage.remove();
            }
        }

        if (!answer) {
            answer = answerChat(cleanQuestion);
        }
        addChatMessage(answer, "bot");
        speakText(answer);
    }

    function startChatMic(button) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const languageModule = getLanguageModule(getLanguage());
        const dictionary = languageModule.translations;
        if (!SpeechRecognition) {
            alert(dictionary.speechNotSupported);
            return;
        }

        const input = document.querySelector("[data-chat-input]");
        if (!input) {
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = languageModule.speechCode;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        button.classList.add("listening");
        button.textContent = dictionary.listening;

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            input.value = transcript;
            submitChat(transcript);
        };

        recognition.onend = () => {
            button.classList.remove("listening");
            button.textContent = dictionary.mic || "Mic";
        };

        recognition.onerror = () => {
            button.classList.remove("listening");
            button.textContent = dictionary.mic || "Mic";
        };

        recognition.start();
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
        document.querySelectorAll("[data-speak-crop]").forEach((button) => {
            button.addEventListener("click", () => speakCrop(button.closest(".crop-card")));
        });
        document.querySelectorAll("[data-crop-search]").forEach((input) => {
            input.addEventListener("input", filterCrops);
        });
        document.querySelectorAll("[data-search-mic]").forEach((button) => {
            button.addEventListener("click", () => startSearchMic(button));
        });
        document.querySelectorAll("[data-chat-toggle]").forEach((button) => {
            button.addEventListener("click", openChatbot);
        });
        document.querySelectorAll("[data-chat-close]").forEach((button) => {
            button.addEventListener("click", closeChatbot);
        });
        document.querySelectorAll("[data-chat-form]").forEach((form) => {
            form.addEventListener("submit", (event) => {
                event.preventDefault();
                const input = form.querySelector("[data-chat-input]");
                submitChat(input.value);
                input.value = "";
            });
        });
        document.querySelectorAll("[data-chat-mic]").forEach((button) => {
            button.addEventListener("click", () => startChatMic(button));
        });
        document.querySelectorAll("[data-chat-suggestion]").forEach((button) => {
            button.addEventListener("click", () => submitChat(button.textContent));
        });
        filterCrops();
    });
})();
