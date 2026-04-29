var randPost = GetRandom(postsArray);

const mainDomain = "gplinks.com";
const redirectDomain = "gplinks.co";

var link_id = getQueryParam("lid");
var pub_id = getQueryParam("pid");
var plan_id = getQueryParam("plid");
var visitor_id = getQueryParam("vid");
var type = getQueryParam("type");

var push_offer_id = 3;
var push_offer_type = 2;
var iframe_offer_id = 4;
var iframe_offer_type = 3;

// Set the cookie expiration time to 10 minutes from now
var expireTime = new Date(new Date().getTime() + 10 * 60 * 1000); // 10 mins

if (pub_id !== null && plan_id !== null && link_id !== null && visitor_id !== null) {

  Cookies.set("lid", link_id, {
    expires: expireTime,
  });
  Cookies.set("vid", visitor_id, {
    expires: expireTime,
  });
  Cookies.set("pid", pub_id, {
    expires: expireTime,
  });
  Cookies.set("sid", 0, {
    expires: expireTime,
  });
  Cookies.set("plid", plan_id, {
    expires: expireTime,
  });
  Cookies.set("type", type, {
    expires: expireTime,
  });
  Cookies.set("imps", 0, {
    expires: expireTime,
  });

    // window.location.href = randPost;
     window.location.href = window.location.origin;
    
}

if (Cookies.get("pid") && Cookies.get("lid") && Cookies.get("vid")) {
  var cookie_pub_id = Cookies.get("pid");
  var cookie_link_id = Cookies.get("lid");
  var cookie_visitor_id = Cookies.get("vid");
  var cookie_type = Cookies.get("type");
  var cookie_step_id = Number(Cookies.get("sid"));
  var cookie_pub_plan_id = Number(Cookies.get("plid"));
  var StepsToGo = getStepsToGo(cookie_pub_plan_id);

  let target_final =
    `https://${redirectDomain}/${cookie_link_id}/?pid=${cookie_pub_id}&vid=${cookie_visitor_id}&type=${cookie_type}` 

   next_status = cookie_step_id + 1;

  if (cookie_step_id + 1 >= StepsToGo) {
    next_target = target_final;
    readyToGo = true;
  } else {
    next_target = randPost;
    readyToGo = false;
  }
}

jQuery(function ($) {
  var isOverGoogleAd = false;
  $("iframe[ id *= google ]")
    .mouseover(function () {
      isOverGoogleAd = true;
    })
    .mouseout(function () {
      isOverGoogleAd = false;
    });

  $(window).blur(function () {
      if (isOverGoogleAd) {
        // sendPostback(cookie_pub_id,cookie_visitor_id,iframe_offer_id,iframe_offer_type);
      }
  }).focus();

  function sendPostback(pubId, visitorId, offerId, offerType) {
    const postbackImage = new Image();
    postbackImage.src =
      `https://${mainDomain}/track/data.php?request=addConversion&pid=` +
      pubId +
      "&vid=" +
      visitorId +
      "&o_id=" +
      offerId +
      "&o_type=" +
      offerType;
  }
});


window.googletag = window.googletag || { cmd: [] };

googletag.cmd.push(function () {
  googletag.pubads().addEventListener("impressionViewable", (event) => {
       AddImps();
  });
});

function AddImps(){
  var expireTime = new Date(new Date().getTime() + 10 * 60 * 1000); // 10 mins
  var AdImps = Number(Cookies.get("imps"));
  Cookies.set("imps", AdImps + 1, {
    expires: expireTime,
  });
}

if (cookie_pub_id) {
  gtag("set", "user_properties", {
    pid: cookie_pub_id,
  });
}

$(document).ready(function () {
  $("#VerifyBtn").on("click", async function () {
    $("#VerifyBtn").html("Please Wait...");
    var expireTime = new Date(new Date().getTime() + 10 * 60 * 1000); // 10 mins
    var AdImps = Number(Cookies.get("imps"));
    if (readyToGo == true){
    var setVisitor_response = await setVisitor(next_status, AdImps, cookie_visitor_id);
    var ustatus = setVisitor_response.success;
    if (ustatus) {
      Cookies.set("sid", next_status, {
        expires: expireTime,
      });
      Cookies.set("imps", 0, {
        expires: expireTime,
      });
    }
    } else {
      Cookies.set("sid", next_status, {
        expires: expireTime,
      });
    }
      $("#VerifyBtn").hide();
      $("#GoNewxtDiv").show();
      $("#NextBtn").attr("href", next_target);
      $("#StepInfo").text("Step " + next_status + " of " + StepsToGo);
      console.log(readyToGo);
  });
});

function getStepsToGo(user_plan_id) {
  switch (user_plan_id) {
    case 1:
      return 3;
    case 2:
      return 2;
    case 3:
      return 1;
    case 11:
      return 3;
    case 12:
      return 3;
    default:
      return 3;
  }
}

function GetRandom(postsArray) {
  var randomIndex = Math.floor(Math.random() * postsArray.length);
  var randomString = postsArray[randomIndex];
  return randomString;
}

function getQueryParam(param) {
  var urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

function BlockedPermission() {
  // Push promt closed or blocked
}

async function handleAllowPermission() {
  // permission granted
  var conversionResponse = await addConversion(
    cookie_pub_id,
    cookie_visitor_id,
    push_offer_id,
    push_offer_type
  );
  var cstatus = conversionResponse.status;
}

(function handlePermission() {
  try {
    return navigator.permissions
      .query({
        name: "notifications",
      })
      .then(permissionQuery)
      .catch(onerror);
  } catch (error) {
    // Handle the error here, or return a default value
    console.error("navigator.permissions.query not supported:", error);
    // Return a default value or handle it as needed
    return null;
  }
})();

function permissionQuery(result) {
  var newPrompt;
  result.onchange = function () {
    if (result.state == "granted") {
      handleAllowPermission();
    } else if (result.state == "prompt") {
      // we can ask the user
      Notification.requestPermission();
    } else if (result.state == "denied") {
      BlockedPermission();
    } else {
      // we can ask the user
      Notification.requestPermission();
    }
  };
  return newPrompt || result;
}

function getVisitor(visitor_id) {
  return $.ajax({
    type: "GET",
    // make sure you respect the same origin policy with this url:
    url: `https://${mainDomain}/track/data.php`,
    data: {
      request: "getVisitor",
      vid: visitor_id,
    },
    dataType: "json",
  });
}

function getUser(user_id) {
  return $.ajax({
    type: "GET",
    // make sure you respect the same origin policy with this url:
    url: `https://${mainDomain}/track/data.php`,
    data: {
      request: "getUser",
      uid: user_id,
    },
    dataType: "json",
  });
}

function setVisitor(status, impressions, visitorId) {
  return $.ajax({
  type: "GET",
  url: `https://${mainDomain}/api/update-visitor-value`,
  data: {
    vid: visitorId,  // `visitorId` must already be a numeric value
    value: status,    // `points` is what you previously called `impressions` or similar
    impressions: impressions    // `points` is what you previously called `impressions` or similar
  },
  dataType: "json"
});
}

function addConversion(pubId, visitorId, offerId, offerType) {
  return $.ajax({
    type: "POST",
    // make sure you respect the same origin policy with this url:
    url: `https://${mainDomain}/track/data.php`,
    data: {
      request: "addConversion",
      pid: pubId,
      vid: visitorId,
      o_id: offerId,
      o_type: offerType,
    },
    dataType: "json",
  });
}

var SmileyBanner = document.getElementById("SmileyBanner");
var count = 15;
var timerInterval;
var Intervaltime = 2000;

if (cookie_pub_plan_id == 12) {
  Intervaltime = 1000;
  $(document).ready(function() {
    $(".VerifyBtn, .NextBtn").css("background-color", "#482dff");
  });
}

if (SmileyBanner) {
  count = 10;
  Intervaltime = 1000;
}

function isPageVisible() {
  var SmileyBanner = document.getElementById("SmileyBanner");
  if (SmileyBanner) {
    // Set an interval to monitor the active element for iframes.
    var monitor = setInterval(function () {
      var elem = document.activeElement;
      if (elem && elem.tagName == 'IFRAME') {
        $(".SmileyBanner").css("display", "none");
        setTimeout(function () {
          $(".myWaitingDiv").css("display", "block");
        }, 3000);
        SetAdCookie();
        setTimeout(function () {
           goVerified();
        }, 10000);
        clearInterval(monitor); // Clear the interval.
        return !document.hidden; // return for on-screen 
      }
    }, 100);
  } else {
      return !document.hidden; // return for on-screen 
  }
}

function goVerified(){
    var gpProgressBar = document.getElementById("gp_progress-bar");
    var timerDiv = document.getElementById("myTimerDiv");
    var nextInst = document.getElementById("myNextInst");
    var verifyBtn = document.getElementById("VerifyBtn");
    var myWaitingDiv = document.getElementById("myWaitingDiv");

    if (gpProgressBar) {
      gpProgressBar.style.display = "none";
    } else if (timerDiv) {
      timerDiv.style.display = "none";
    }
    if (nextInst) {
      nextInst.style.display = "block";
    }
    if (verifyBtn) {
      verifyBtn.style.display = "block";
    }
    if (myWaitingDiv) {
      myWaitingDiv.style.display = "none";
    }
}

function keepClosed(){
  var verifyBtn = document.getElementById("VerifyBtn");
  if (verifyBtn) {
    verifyBtn.style.display = "none";
  }
}

function SetAdCookie(){
  // Set the cookie time to 2 minutes from now
  var expireTime = new Date(new Date().getTime() + 2 * 60 * 1000); // 2 minutes 
  Cookies.set("adexp", 1, {
    expires: expireTime,
  });
}

function timer() {
  count = count - 1;

  if (cookie_pub_plan_id == 12) {
    var progressBar = document.getElementById("gp_progress");
    if (progressBar) {
      var progress = ((15 - count) / 15) * 100;
      progressBar.style.width = progress + "%";
    }
  }
  
  if (count <= 0) {
    goVerified();
    clearInterval(timerInterval);
  } else {
    keepClosed();
  }
  
  var myTimerElement = document.getElementById("myTimer");
  if (myTimerElement) {
    myTimerElement.innerHTML = count;
  }
  
}

$(document).ready(function () {
  if (isPageVisible()) {
    timerInterval = setInterval(timer, Intervaltime);
  }

  $(document).on('visibilitychange', function () {
    if (isPageVisible()) {
      timerInterval = setInterval(timer, Intervaltime);
    } else {
      clearInterval(timerInterval);
    }
  });
});


// AdBlock Detector START

(function () {
  const html = `
    <style>
      .adb-popup { font-family: Arial, sans-serif; }
      .adb-overlay {
        z-index: 10001;
        position: fixed; top: 0; bottom: 0; left: 0; right: 0;
        width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(3px);
        visibility: hidden; opacity: 1;
        transition: opacity 500ms;
      }
      .adb-popup {
        margin: 70px auto; padding: 20px;
        background: #fff; border-radius: 5px;
        width: 30%; position: relative;
        transition: all 0.5s ease-in-out;
      }
      .adb-popup h2 {
        margin-top: 0; color: #333;
        font-size: 1.5em; font-weight: bold;
        text-align: center;
      }
      .adb-popup .content {
        min-height: 30%; overflow: auto;
      }
      .adb-message {
        font-size: 16px; margin-top: 15px;
        margin-bottom: 15px; text-align: center;
      }
      .adb-align-center {
        display: flex; justify-content: center;
        align-items: center; flex-direction: column;
      }
      .button-adb-refresh {
        background-color: #13aa52; border: 1px solid #13aa52;
        border-radius: 4px; color: #fff;
        cursor: pointer; font-size: 16px;
        padding: 10px 25px;
        transition: transform 150ms, box-shadow 150ms;
      }
      .button-adb-refresh:hover {
        box-shadow: rgba(0, 0, 0, 0.15) 0 3px 9px 0;
        transform: translateY(-2px);
      }
      @media screen and (max-width: 768px) {
        .adb-popup { width: 90%; }
      }
    </style>

    <div id="AdbModel" class="adb-overlay" role="dialog" aria-modal="true" aria-labelledby="adb-title">
      <div class="adb-popup adb-align-center">
        <h2 id="adb-title">AdBlocker Detected!</h2>
        <div class="content adb-align-center">
          <img src="https://gplinks.co/img/adblock.png" alt="Ad Block Warning" style="width: 70%; height: auto; margin-top: 10px;" />
          <p class="adb-message">
            Dear visitor, it seems you're using an ad blocker. Please disable it to help us support our publishers and offer free content.<br /><br />
            Note: Brave browser is not supported on our website. Please use a different browser for the best experience.<br /><br />
            Thank you for your cooperation.
          </p>
          <span>Once you're done?</span>
          <button class="button-adb-refresh" onclick="location.reload()" aria-label="Reload page to continue">
            Reload Page
          </button>
        </div>
      </div>
    </div>
  `;

  function injectHTML() {
    const div = document.createElement("div");
    div.innerHTML = html;
    document.body.appendChild(div);
  }

  function AdBDetected() {
    const modal = document.getElementById("AdbModel");
    if (modal) {
      modal.style.visibility = "visible";
      document.body.style.overflow = "hidden";
    }
  }

  function detectWithFakeDiv() {
    const fakeAd = document.createElement("div");
    fakeAd.className = "adsbox ad-unit banner_ads ad-banner text-ads ad-space";
    fakeAd.style.height = "1px";
    fakeAd.style.width = "1px";
    fakeAd.style.position = "absolute";
    fakeAd.style.top = "-9999px";
    document.body.appendChild(fakeAd);

    setTimeout(() => {
      const style = window.getComputedStyle(fakeAd);
      const hidden = style && (style.display === "none" || style.visibility === "hidden");
      const invisible = fakeAd.offsetHeight === 0 || fakeAd.offsetParent === null;

      fakeAd.remove();

      if (hidden || invisible) {
        AdBDetected();
      }
    }, 250);
  }

  async function detectBlockedScripts() {
    if (!navigator.onLine) return;

    let adBlocked = false;
    const targets = [
      "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
      "https://api.gplinks.com/track/js/main.js"
    ];

    for (let url of targets) {
      try {
        await fetch(new Request(url, { method: "HEAD", mode: "no-cors" }))
          .catch(() => (adBlocked = true));
      } catch {
        adBlocked = true;
      }
    }

    if (adBlocked) AdBDetected();
  }

  async function detectBrave() {
    if (navigator.brave) {
      const is = await navigator.brave.isBrave();
      if (is) AdBDetected();
    }
  }

  function initAdblockDetector() {
    injectHTML();
    detectWithFakeDiv();
    detectBlockedScripts();
    detectBrave();

    // optional anti-anti detection
    if (window.blockAdBlock !== undefined) {
      AdBDetected();
    }
  }

  if (document.readyState === "loading") {
    window.addEventListener("load", initAdblockDetector);
  } else {
    initAdblockDetector();
  }
})();

// AdBlock Detector END
