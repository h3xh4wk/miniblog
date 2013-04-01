String.prototype.count = function(s1) { 
    return (this.length - this.replace(new RegExp(s1,"g"), '').length) / s1.length;
}

function autoSave() {
    if (!supportsLocalStorage()) { return false; }
    load();
    
    var autosaveTimer;
    $('textarea').keyup(function(e) {
        if(autosaveTimer){ clearTimeout(autosaveTimer); }
        autosaveTimer = setTimeout(save, 2000);
    });
    
    $('#blog-post').submit(function() {
        localStorage.clear();
    });
}

function supportsLocalStorage() {
    try {
        return 'localStorage' in window && window['localStorage'] !== null;
    } catch (e) {
        return false;
    }
}

function save() {
    localStorage['post-title'] = $('.post-title').val();
    localStorage['post-body'] = $('.post-body').val();
}

function load() {
    var title = localStorage['post-title'];
    var body = localStorage['post-body'];
    if(title){
        $('.post-title').val( localStorage['post-title'] );
    }      
    if(body){
        $('.post-body').val( localStorage['post-body'] );
    }
}

function handleSpecialKeys() {
    // catch 'tab' key in blog post body
    $('.post-body').keydown(function(e) {
        var standin = '\t';
        var new_line = '\n';
        var multi_line = false;
        var $this, end, start, new_value;
        
        if (e.keyCode === 9) {
            // get selection
            var move_end = 0;
            start = this.selectionStart;
            end = this.selectionEnd;
            selection = $(this).val().substring(start, end);
            multi_line = !(start === end || selection.indexOf('\n') === -1);

            // insert tab(s)
            if(multi_line) {
                new_value = $(this).val()
                                   .substring(start, end)
                                   .split(new_line);
                                   
                $.each(new_value, function(idx, val) {
                    new_value[idx] = standin + val;
                    move_end += standin.length;
                });
                
                new_value = new_value.join(new_line);
            }
            // else replace text with tab
            else {
                new_value = standin;
                move_end = standin.length;
            }
            
            // insert back into textarea
            $(this).val($(this).val().substring(0, start) +
                        new_value +
                        $(this).val().substring(end));
            
            // handle new selection after replacement
            if(multi_line) {
                this.selectionStart = start;
                this.selectionEnd = end + move_end;
            }
            else {
                this.selectionStart = this.selectionEnd = start + move_end;
            }
            
            return false;
        }
    });
    
    // do not allow return ('/r') in blog post title
    $('.post-title').keydown(function(e) {
        if (e.keyCode === 13) {
            e.preventDefault();
        }
    });
}
