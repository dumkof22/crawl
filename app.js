window.sApp = {
    request: function(url, method, data) {
        return $.ajax({
            url: url,
            method: method || 'GET',
            dataType: 'json',
            data: data,
            cache: false
        });
    },
    requestPage: function(url, method, data) {
        return $.ajax({
            url: url,
            method: method || 'GET',
            data: data,
            cache: false
        });
    },
    fillSelect: function(elemSelector, data) {
        var output = '';
        if (typeof(elemSelector) === 'string') {
            if ($(elemSelector).length > 0) {
                $(elemSelector).html('<option value="" selected disabled></option>');
                $.each(data, function(index, row) {
                    output += '<option value="' + row.id + "'>" + row.name + '</option>';
                });

                $(elemSelector).append(output);
            }
        } else {
            elemSelector.html('<option value="" selected disabled></option>');
            $.each(data, function(index, row) {
                output += '<option value="' + row.id + '">' + row.name + '</option>';
            });
            elemSelector.append(output);
        }
    },
    stopLoader: function($element,targetContainer = "") {
        $element = targetContainer != '' ? $(targetContainer) : $element;
        $element.find(".loader").remove();
    },
    startLoader: function($element,targetContainer = "") {
        $element = targetContainer != '' ? $(targetContainer) : $element;
        stopLoader($element);
        $element.append($(".loaderContainer").html());
    },
    init: function() {
        window.showMessage = sApp.showMessage;
        window.placeMessage = sApp.placeMessage
        window.placeMessageDirect = sApp.placeMessageDirect;
        window.stopLoader = sApp.stopLoader;
        window.startLoader = sApp.startLoader;
        $(document).on("submit", "[data-ajax-form=true]", function(e) {
            e.preventDefault();
            var $this = $(this);
            var requestData;
            if (($(this).attr("data-multipart") || '') === "true") {
                requestData = new FormData($this[0]);
            } else {
                requestData = $(this).find("input,select,textarea").serialize();
            }
            var callback = $(this).attr("callback") || $(this).attr("data-callback");
            var loader = $(this).attr("data-ajax-loader") || '';
            var loaderCont = $(this).attr("data-ajax-target-container") || '';
            $this.find(".messages").html('');
            if (loader === "buttonText") {
                $this.find("[type=submit],[data-submitter=true]").find("span.text").text($this.find("[type=submit],[data-submitter=true]").attr("data-loading-text"));
            } else {
                if(loaderCont != ""){
                    startLoader($this,loaderCont);
                }else{
                    startLoader($this);
                }
            }
            var args = {
                url: $this.attr("data-action"),
                type: "POST",
                data: requestData,
                success: function(resp) {
                    stopLoader($this,loaderCont);
                    if (loader === "buttonText") {
                        $this.find("[type=submit],[data-submitter=true]").find("span.text").text($this.find("[type=submit],[data-submitter=true]").attr("data-org-text"));
                    }
                    var messages = '';
                    if (resp.data.state === false && resp.data.message !== undefined)
                        messages += '<div class="alert alert-danger xs-p-10">' + resp.data.message + '</div>';
                    if (messages !== '')
                        $this.find(".messages").append(messages).show();

                    if (callback !== undefined && window[callback] !== undefined)
                        window[callback](resp, $this);
                },
                error: function(request, error) {
                    stopLoader($this);

                    if (request.responseJSON !== undefined) {
                        var messages = '';
                        if (request.responseJSON.data.state === false && request.responseJSON.data.message !== undefined)
                            messages += '<div class="alert alert-danger xs-p-10">' + request.responseJSON.data.message + '</div>';
                        if (messages !== '')
                            $this.find(".messages").append(messages).show();
                    }

                    if (callback !== undefined && window[callback] !== undefined)
                        window[callback](request.responseJSON || {}, $this);
                }
            };
            if (($(this).attr("data-multipart") || '') === "true") {
                args.processData = false;
                args.contentType = false;
            } else {
                args.dataType = "json";
            }
            $.ajax(args);
            return false;
        });

        var tagArr = document.getElementsByTagName("input");
        for (var i = 0; i < tagArr.length; i++) {
            tagArr[i].autocomplete = 'off';
        }

    }
};
jquerySync(function ($){
    window.sApp.init();
});