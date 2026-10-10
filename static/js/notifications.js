/* ParkSmart Nepal - navbar notification bell
   - opens/closes the dropdown
   - refreshes itself every 30 s (overstay / expiry alerts appear without reloading)
   - "Mark all as read" without a page reload 
*/

(function () {
  var root = document.querySelector("[data-notif]");
  if (!root) return;

  var toggle = root.querySelector("[data-notif-toggle]");
  var panel = root.querySelector("[data-notif-panel]");
  var badge = root.querySelector("[data-notif-badge]");
  var list = root.querySelector("[data-notif-list]");
  var readAllForm = root.querySelector("[data-notif-readall]");
  var feedUrl = root.getAttribute("data-feed-url");
  var lastUnread = badge && !badge.hidden ? parseInt(badge.textContent, 10) || 0 : 0;

  function openPanel() {
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
  }
  function closePanel() {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", function (e) {
    e.stopPropagation();
    panel.hidden ? openPanel() : closePanel();
  });
  document.addEventListener("click", function (e) {
    if (!root.contains(e.target)) closePanel();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closePanel();
  });

  function esc(text) {
    var d = document.createElement("div");
    d.textContent = text == null ? "" : String(text);
    return d.innerHTML;
  }

  function setBadge(count) {
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 9 ? "9+" : String(count);
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
    if (count > lastUnread) {
      toggle.classList.remove("ring");
      void toggle.offsetWidth; // restart the animation
      toggle.classList.add("ring");
    }
    lastUnread = count;
  }

  function render(items) {
    if (!items.length) {
      list.innerHTML = '<li class="notif-empty">You\'re all caught up. No notifications yet.</li>';
      return;
    }
    list.innerHTML = items
      .map(function (n) {
        return (
          "<li>" +
          '<a href="' + esc(n.url) + '" class="notif-item kind-' + esc(n.kind) + (n.is_read ? "" : " unread") + '">' +
          '<span class="notif-dot"></span>' +
          '<span class="notif-body"><strong>' + esc(n.title) + "</strong>" +
          "<span>" + esc(n.message) + "</span>" +
          "<small>" + esc(n.time) + "</small></span>" +
          "</a></li>"
        );
      })
      .join("");
  }

  function refresh() {
    if (document.hidden) return;
    fetch(feedUrl, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        render(data.items);
        setBadge(data.unread);
      })
      .catch(function () {});
  }

  if (readAllForm) {
    readAllForm.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(readAllForm.action, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: new FormData(readAllForm),
      }).then(function () {
        lastUnread = 0;
        setBadge(0);
        refresh();
      });
    });
  }

  setInterval(refresh, 30000);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) refresh();
  });
})();