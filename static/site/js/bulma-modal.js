'use strict';

/*
How to use this script

First, create a modal like this
<div class="modal" id="my-unique-modal-identifier">
  <div class="modal-background"></div>
  <div class="modal-content">
    <!-- Any other Bulma elements you want -->
  </div>
  <button class="modal-close is-large" aria-label="close"></button>
</div>

The div class has a unique ID to identify this particular modal.

Next, you create a button (or some other element that you can interact with) like this:
<button class="button modal-button" data-target="my-unique-modal-identifier">
  Open the modal!
</button>

See how the `data-target` matches the id of the modal we want to open? This is important.

Once this is set up and this script is loaded, the button should open the modal!
*/

document.addEventListener('DOMContentLoaded', function () {
  var rootEl = document.documentElement;
  var $modals = _getAll('.modal');
  var $modalButtons = _getAll('.modal-button');
  var $modalCloses = _getAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button');

  // Add click event listeners to all the modal buttons,
  // which are buttons with the .modal-button class.
  if ($modalButtons.length > 0) {
    $modalButtons.forEach(function ($el) {
      $el.addEventListener('click', function () {
        var target = $el.dataset.target;
        var $target = document.getElementById(target);
        rootEl.classList.add('is-clipped');
        $target.classList.add('is-active');
      });
    });
  }

  // Add click event listeners to all close icons, like an X
  // icon in the top right corner of the modal window.
  if ($modalCloses.length > 0) {
    $modalCloses.forEach(function ($el) {
      $el.addEventListener('click', function () {
        closeModals();
      });
    });
  }

  // Close the modal if the user hits the escape key
  document.addEventListener('keydown', function (event) {
    var e = event || window.event;
    if (e.keyCode === 27) {
      closeModals();
    }
  });

  // Model closing logics
  function closeModals() {
    rootEl.classList.remove('is-clipped');
    $modals.forEach(function ($el) {
      $el.classList.remove('is-active');
    });
  }

  // Helper function to fetch all elements with certain classes.
  function _getAll(selector) {
    return Array.prototype.slice.call(document.querySelectorAll(selector), 0);
  }
});
