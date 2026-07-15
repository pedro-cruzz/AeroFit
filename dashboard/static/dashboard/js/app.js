function tickCountdown(element) {
    if (!element) return;

    const parts = element.textContent.trim().split(":").map(Number);
    let totalSeconds = (parts[0] * 3600) + (parts[1] * 60) + parts[2];

    setInterval(() => {
        totalSeconds = Math.max(totalSeconds - 1, 0);
        const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
        const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
        const seconds = String(totalSeconds % 60).padStart(2, "0");
        element.textContent = `${hours}:${minutes}:${seconds}`;
    }, 1000);
}

tickCountdown(document.querySelector("#leagueCountdown"));
