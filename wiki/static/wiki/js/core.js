function ajaxError(){}

$.ajaxSetup({
  timeout: 7000,
  cache: false,
  error: function(e, xhr, settings, exception) {
      ajaxError();
  }
});

function jsonWrapper(url, callback) {
  $.getJSON(url, function(data) {
    if (data == null) {
      ajaxError();
    } else {
      callback(data);
    }
  });
}

/* -------------------------------------------------------
   Bulma navbar burger toggle
   ------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', function() {
  var burgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
  burgers.forEach(function(el) {
    el.addEventListener('click', function() {
      var target = document.getElementById(el.dataset.target);
      el.classList.toggle('is-active');
      if (target) target.classList.toggle('is-active');
    });
  });
});

/* -------------------------------------------------------
   Bulma dropdown toggle (click-based)
   ------------------------------------------------------- */
$(document).on('click', '.wiki-dropdown-trigger', function(e) {
  e.preventDefault();
  e.stopPropagation();
  $(this).closest('.dropdown').toggleClass('is-active');
});
$(document).on('click', function() {
  $('.dropdown').removeClass('is-active');
});

/* -------------------------------------------------------
   Notification delete button
   ------------------------------------------------------- */
$(document).on('click', '.notification .delete', function() {
  $(this).closest('.notification').remove();
});

/* -------------------------------------------------------
   Bootstrap modal() shim → Bulma is-active
   ------------------------------------------------------- */
$.fn.modal = function(action) {
  return this.each(function() {
    var $modal = $(this);
    if (action === 'show' || action === undefined) {
      $modal.addClass('is-active');
    } else if (action === 'hide') {
      $modal.removeClass('is-active');
    } else if (action === 'toggle') {
      $modal.toggleClass('is-active');
    }
  });
};

$(document).on('click', '[data-dismiss="modal"]', function() {
  $(this).closest('.modal').removeClass('is-active');
});

$(document).on('click', '.modal-background, .modal-close', function() {
  $(this).closest('.modal').removeClass('is-active');
});

/* -------------------------------------------------------
   Bootstrap collapse() shim → wiki-collapse is-active
   ------------------------------------------------------- */
$.fn.collapse = function(action) {
  return this.each(function() {
    if (action === 'show') {
      $(this).addClass('is-active');
    } else if (action === 'hide') {
      $(this).removeClass('is-active');
    } else if (action === 'toggle') {
      $(this).toggleClass('is-active');
    }
  });
};

$(document).on('click', '[data-toggle="collapse"]', function(e) {
  e.preventDefault();
  var target = $(this).attr('href') || $(this).data('target');
  $(target).toggleClass('is-active');
});
