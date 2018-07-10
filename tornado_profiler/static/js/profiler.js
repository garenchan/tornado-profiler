$(function() {
    var current_path = window.location.pathname;
    URL_PREFIX = current_path.split('/')[1];
    DATE_FORMAT = "MM/DD/YYYY hh:mm A";
    current_request = null;
    
    if ($('[data-toggle="select"]').length) {
        $('[data-toggle="select"]').select2();
    }
    
    $("#begin-time-filter").daterangepicker({
        timePicker: true,
        //timePickerSeconds: true,
        autoApply:false,
        ranges: {
           "Today": [moment().startOf("days"), moment()],
           'Yesterday': [moment().subtract(1, 'days').startOf("days"), moment().subtract(1, 'days').endOf("days")],
           'Last 7 Days': [moment().subtract(6, 'days'), moment()],
           'Last 30 Days': [moment().subtract(29, 'days'), moment()],
           'This Month': [moment().startOf('month'), moment()],
           'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        },
        locale: {
          format: DATE_FORMAT
        },
        buttonClasses: "btn",
        applyClass: "btn-embossed btn-primary",
        cancelClass: "btn-default",
    });
    
    groups_table = $("#groups-table").DataTable({
        "bServerSide": true,
        "bProcessing": true,
        "bAutoWidth": false,
        "sAjaxSource": "/" + URL_PREFIX + "/api/measurements/groups/",
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
            {"sTitle": "avg_elapsed/s", "mData": "avg", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ){
                return data;
            }},
            {"sTitle": "max_elapsed/s", "mData": "max", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ) {
                return data;
            }},
            {"sTitle": "min_elapsed/s", "mData": "min", "sWidth": "15%", "bSearchable": false, "bSortable": true, "mRender": function (data, type, row ) {
                return data;
            }},
        ],
        "aaSorting": [[2, 'desc']],
    });
    
    measurements_table = $("#measurements-table").DataTable({
        "bServerSide": true,
        "bProcessing": true,
        "deferLoading": 0,
        "bAutoWidth": false,
        "dom": 'lrtip',
        "sAjaxSource": "/" + URL_PREFIX + "/api/measurements/",
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
            {"sTitle": "elapse_time/s", "mData": "elapse_time", "sWidth": "30%", "bSearchable": true, "bSortable": true, "mRender": function (data, type, row ) {
                return data;
            }},
            {"sTitle": "begin_time", "mData": "begin_time", "sWidth": "30%", "bSearchable": true, "bSortable": true, "mRender": function (data, type, row ) {
                return moment.unix(data).format("MM/DD/YYYY hh:mm:ss.SSS A");
            }},
        ],
        "aaSorting": [[2, 'desc']],
    });
    
    measurements_table.columns().every(function() {
        var that = this;
        
        $("select", this.footer()).on("change", function() {
            if (that.search() != this.value) {
                that.search(this.value).draw();
            }
        });
        $("input", this.footer()).on("keyup change", function(){
            var value = getColumnSearchValue(this.id, this.value);
            if (that.search() != value) {
                that.search(value).draw();
            }
        });
    });
    
    // force measurements table to draw the first time.
    triggerRedraw();
    
    groups_table.on("click", "tbody tr", function(){
        var data = groups_table.row(this).data();
        $('a[href="#tab-filtering"]').tab("show");
        // trigger measurements table redraw
        $("#method-filter").select2("val", data.method);
        $("#name-filter").val(data.name);
        triggerRedraw();
    });
    
    measurements_table.on("click", "tbody tr", function(){
        var data = measurements_table.row(this).data();
        showContext(data.id);
    });
    hljs.initHighlightingOnLoad();
});

/*custom function use to switch tabs*/
function activeTab(tab) {
    $("#navbar>.navbar-nav>li.active").removeClass("active");
    $(".tab-content>.tab-pane.active").removeClass("active");
    $('a[href="#' + tab + '"]').parent("li").addClass("active");
    $('#' + tab).addClass("active");
}

function getColumnSearchValue(id, value) {
    var value = value !== undefined? value: $("#" + id).val();
    
    if (id == "begin-time-filter") {
        var split_array = value.split('-');
        if (split_array.length == 1) {
            var start_date = split_array[0];
            start_date = moment(start_date, DATE_FORMAT).unix();
            if (isNaN(start_date)) {
                value = "";
            } else {
                value = start_date + '-';
            }
        } else if (split_array.length == 2) {
            var start_date = split_array[0];
            var end_date = split_array[1];
            start_date = moment(start_date, DATE_FORMAT).unix();
            end_date = moment(end_date, DATE_FORMAT).unix();
            if (isNaN(start_date) && isNaN(end_date)) {
                value = "";
            } else if (!isNaN(start_date) && isNaN(end_date)) {
                value = start_date + '-';
            } else if (isNaN(start_date) && !isNaN(end_date)) {
                value = '-' + end_date;
            } else {
                value = start_date + '-' + end_date;
            }
        } else {
            value = "";
        }
    } else if (id == "elapse-time-filter") {
        var float_val = parseFloat(value);
        if (isNaN(float_val)) {
            value = "";
        } else {
            value = float_val.toString();
        }
    }
    
    return value;
}

/*trigger measurements table to search all columns and draw*/
function triggerRedraw() {
    column_map = {
        0: "method-filter",
        1: "name-filter",
        2: "elapse-time-filter",
        3: "begin-time-filter",
    }
    for(var index in column_map) {
        var value = getColumnSearchValue(column_map[index]);
        if (value)
            measurements_table.column(index).search(value);
    }
    measurements_table.draw();
}

/*get and show a measurement's context*/
function showContext(id) {
    if (current_request != null)
        current_request.abort();
    
    current_request = $.ajax({
        type: "GET",
        url: "/" + URL_PREFIX + "/api/measurements/" + id,
        beforeSend:function() {
            $("#meas-context-dialog").modal("hide");
        },
        success: function(data) {
            console.log(data);
            $("#meas-context-dialog-title").text("Measurement-" + id);
            console.log(JSON.stringify(data.measurement.context));
            $("#meas-context-dialog-context").text(JSON.stringify(data.measurement.context));
            $('#meas-context-dialog-body').each(function(i, e) {hljs.highlightBlock(e)});
            $("#meas-context-dialog").modal("show");
        }
    });
}
