$(document).ready(function() {
    // initialise combos for dirty page refreshes
    $('#showsort').val('original');
    $('#showsortdirection').val('asc');

    var $container = [$('#container')];
    $.each($container, function () {
        this.isotope({
            itemSelector: '.trakt_show',
            sortBy: 'original-order',
            layoutMode: 'fitRows',
            getSortData: {
                name: function(itemElem) {
                    var name = $(itemElem).attr('data-name') || '';
                    return (MEDUSA.info.sortArticle ? name : name.replace(/^(The|A|An)\s/i, '')).toLowerCase(); // eslint-disable-line no-undef
                },
                rating: '[data-rating] parseInt',
                votes: '[data-votes] parseInt'
            }
        });
    });

    $('#showsort').on('change', function() {
        var sortCriteria;
        switch (this.value) {
            case 'original':
                sortCriteria = 'original-order';
                break;
            case 'rating':
                /* randomise, else the rating_votes can already
                 * have sorted leaving this with nothing to do.
                 */
                $('#container').isotope({sortBy: 'random'});
                sortCriteria = 'rating';
                break;
            case 'rating_votes':
                sortCriteria = ['rating', 'votes'];
                break;
            case 'votes':
                sortCriteria = 'votes';
                break;
            default:
                sortCriteria = 'name';
                break;
        }
        $('#container').isotope({
            sortBy: sortCriteria
        });
    });

    $('#showsortdirection').on('change', function() {
        $('#container').isotope({
            sortAscending: (this.value === 'asc')
        });
    });
});
