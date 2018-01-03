/* global module */

"use strict";

var posts = {
    ensembleSettings: '/api/ensemble/settings/',
    ensembleResume: '/api/ensemble/resume/',
    ensembleStop: '/api/ensemble/cancel/',
    ensembleShare: '/api/ensemble/share/',
    ensembleAddModel: '/api/ensemble/add/'
};

var gets = {
    ensemble: function(params) {
        return '/api/train/state/?ensemble=' + params.id;
    }
};

var post = function(data, done, error) {
    $.ajax({
        url: posts[this],
        type: 'POST',
        data: JSON.stringify(data, null, 2),
        dataType: 'json'
    }).done(done).error(error);
};

module.exports = {post: {}, get: {}};

for (var key in posts) {
    if (posts.hasOwnProperty(key)) {
        module.exports.post[key] = post.bind(key);
    }
}

for (var key in gets) {
    if (gets.hasOwnProperty(key)) {
        module.exports.get[key] = gets[key].bind(null);
    }
}
