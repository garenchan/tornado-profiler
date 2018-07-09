$(function() {
    var current_path = window.location.pathname;
    var url_prefix = current_path.split('/')[1];
    
    var groups_table = $("#groups-table").DataTable({
        "bServerSide": true,
        "bProcessing": true,
        "sAjaxSource": "/" + url_prefix + "/api/measurements/groups/",
        "lengthMenu": [
            [10, 25, 50, 100],
            [10, 25, 50, 100],
        ],
        "iDisplayLength": 10,
        "aoColumns": [
            {"sTitle": "method", "mData": "method", "sWidth": "10%", "bSearchable": true, "bSortable": false, "mRender": function (data, type, row ){
                return  data;
            }},
            {"sTitle": "name", "mData": "name", "sWidth": "30%", "bSearchable": true, "bSortable": false, "mRender": function (data, type, row ){
                return data;
            }},
            {"sTitle": "count", "mData": "count", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ){
                return data;
            }},
            {"sTitle": "avg_elapsed", "mData": "avg", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ){
                return data;
            }},
            {"sTitle": "max_elapsed", "mData": "max", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ) {
                return data;
            }},
            {"sTitle": "min_elapsed", "mData": "min", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ) {
                return data;
            }},
        ],
        "aaSorting": [[2, 'desc']],
    });
    
        
    groups_table.on("click", "tbody tr", function(){
        console.log(groups_table.row(this).data());
        $('[data-target="#tab-filtering"]').tab("show");
    });
});

function activeTab(tab) {
    console.log('.navbar-nav a[href="#' + tab + '"]');
    $('.navbar-nav a[href="#' + tab + '"]').tab("show");
    
}