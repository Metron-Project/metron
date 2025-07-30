/*****
 * A DOMContentLoaded event listener for use with Bulma that connects the "click" event of each
 * navbar-burger element with the navbar-menu referred to by ID in the "data-target" attribute.
 *
 * This file is a slightly modified version of the example found in the Bulma documentation for
 * the navbar component. It's been updated for some of the newer Javascript standards, but will
 * otherwise behave in exactly the same way.
 *
 * Bulma documentation page: https://bulma.io/documentation/components/navbar/#navbarJsExample
 *****/

document.addEventListener('DOMContentLoaded', () => {

  // Get all "navbar-burger" elements
  const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);

  // Check if there are any navbar burgers
  if ($navbarBurgers.length > 0) {

    // Add a click event on each of them
    $navbarBurgers.forEach($el => {
      $el.addEventListener('click', function () {

        // Get the target from the "data-target" attribute
        const target = $el.dataset.target;
        const $target = document.getElementById(target);

        // Toggle the class on both the "navbar-burger" and the "navbar-menu"
        $el.classList.toggle('is-active');
        $target.classList.toggle('is-active');
      });
    });
  }
});
