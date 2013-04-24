// TODO: make reusable - autoSave(elements list, autoSave refresh time)
(function autoSave() {

    // sets storage to True if localStorage exists (and works as expected)
    var storage, fail, uid;
    try {
      uid = new Date;
      (storage = window.localStorage).setItem(uid, uid);
      fail = storage.getItem(uid) != uid;
      storage.removeItem(uid);
      fail && (storage = false);
    } catch(e) {}

    if (storage) {
        var post_title = document.getElementById('post-title');
        var post_body = document.getElementById('post-body');
    
        // load from localStorage *if* starting fresh
        if (!post_title.value && !post_body.value) {
            post_title.value = storage.getItem('post-title');
            post_body.value = storage.getItem('post-body');
        }
        
        // set timer to save every so often (after user stops typing)
        var autosaveTimer;
        document.onkeyup = function(e) {
            if (autosaveTimer) { clearTimeout(autosaveTimer); }
            autosaveTimer = setTimeout(function(){
                // save to localStorage
                storage.setItem('post-title', post_title.value);
                storage.setItem('post-body', post_body.value);
            }, 1000);
        };
        
        // clear storage on submit (if fields filled out)
        document.getElementById('blog-post').onsubmit = function() {
            if (post_title.value && post_body.value) {
                storage.clear();
            }
        };
    }
})();

(function handleSpecialKeys() {

    // catch 'tab' key in blog post body
    var post_body = document.getElementById('post-body');
    post_body.onkeydown = function(e) {
        var tab = '\t';
        var new_line = '\n';
        var multi_line = false;
        var start, end, selection, selection_value;
        
        if (e.keyCode === 9) {
            e.preventDefault();
        
            // get selection
            var move_end_selection = 0;
            start = post_body.selectionStart;
            end = post_body.selectionEnd;
            selection = String(window.getSelection());
            
            var new_line_index = selection.indexOf('\n');
            multiple_line = !(start === end || new_line_index === -1);

            // insert tab(s) if multiple lines selected
            if(multiple_line) {
                selection_value = selection.split(new_line);
                
                for (var i = 0; i < selection_value.length; i++) {                 
                    selection_value[i] = tab + selection_value[i];
                    move_end_selection += tab.length;
                }
                
                selection_value = selection_value.join(new_line);
            }
            // else replace text with tab
            else {
                selection_value = tab;
                move_end_selection = tab.length;
            }
            
            // insert back into textarea
            post_body.value = post_body.value.substring(0, start) +
                              selection_value +
                              post_body.value.substring(end);
            
            // handle new selection after replacement
            if(multiple_line) {
                post_body.selectionStart = start;
                post_body.selectionEnd = end + move_end_selection;
            }
            else {
                post_body.selectionStart =
                post_body.selectionEnd =
                start + move_end_selection;
            }
        }
    };
    
    // catch 'return' key in blog post title
    document.getElementById('post-title').onkeydown = function(e) {
        if (e.keyCode === 13) {
        
            // do not allow multiline titles
            e.preventDefault();
        }
    };
})();
