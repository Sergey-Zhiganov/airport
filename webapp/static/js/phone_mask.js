if (typeof jQuery === "undefined") {
    var script = document.createElement('script');
    script.src = "https://code.jquery.com/jquery-3.6.0.min.js";
    document.head.appendChild(script);
}

var maskScript = document.createElement('script');
maskScript.src = "https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js";
document.head.appendChild(maskScript);

document.addEventListener("DOMContentLoaded", function() {
    function initMask() {
        if (typeof jQuery !== "undefined" && typeof jQuery.fn.mask !== "undefined") {
            
            $('input[phone="true"]').each(function() {
                $(this).mask('+7 (000) 000-00-00');
                
                $(this).closest('form').submit(function() {
                    var val = $(this).find('input[phone="true"]').val();
                    $(this).find('input[phone="true"]').val(val.replace(/\D/g, ''));
                });
            });

        } else {
            setTimeout(initMask, 50);
        }
    }

    initMask();
});