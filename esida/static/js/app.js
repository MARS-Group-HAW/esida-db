const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl))


$(document).ready(function() {
    $('.js-datatable').DataTable({
      pageLength: 25,
      columnDefs: [
        {targets: 'no-sort', orderable: false }
    ]
    });
} );
