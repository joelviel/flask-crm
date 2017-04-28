function resetTimer(customerKey){
    $('#CustomerTableContainer').jtable('updateRecord', {
        record: {
            key: customerKey,
            timer: new Date().getTime().toString()
        }
    });
}


$(document).ready(function () {

    function getTimer(date_before_int){

        var now = new Date();

        var date_before = new Date(date_before_int);

        var delta = (now - date_before) / 1000;

        var months = Math.floor(delta / 2628000);
        delta -= months * 2628000;

        var weeks = Math.floor(delta / 604800);
        delta -= weeks * 604800;

        var days = Math.floor(delta / 86400);
        delta -= days * 86400;

        var hours = Math.floor(delta / 3600) % 24;
        delta -= hours * 3600;

        var minutes = Math.floor(delta / 60) % 60;
        delta -= minutes * 60;

        var seconds = Math.floor(delta % 60);

        if (months > 0) return months + 'Mo ' + weeks + 'We ' + days + 'd ' + hours + 'h'
        else if (weeks > 0) return  weeks + 'We ' + days + 'd ' + hours + 'h'
        else if (days  > 1) return  days + 'days ' + hours + 'h'
        else if (days  > 0) return  days + 'day '  + hours + 'h'
        else if (hours > 1) return  hours + 'hours'
        else if (hours > 0) return  hours + 'hour'
        else if (hours <= 0 && minutes <= 1) return  'less than 1 minute'
        else return 'less than 1 hour'
        //":" + timePadding(minutes) + ":" + timePadding(seconds);

    }


    // compute timers
    function updateTimers() {$( ".dynamic-timer" ).each(function() {$(this).text(getTimer(parseInt($( this ).attr('data-start'))));})}

    // update timers every 10 sec
    setInterval(function(){updateTimers();}, 10000);


    function api_url(model, jtParams) {
        return jtParams? '/customers?&jtSorting='.concat(jtParams.jtSorting) : '/customers'
    }


    function listToTags(list, colorThem){
        
        // specific to the plugin jQuery tagsInput
        if (typeof list == "string")
            list = list.trim().split(',')

        var display = '';

            for(var i=0; i<list.length; i++) {
                if (colorThem) {
                    tagColor = jtableTagColors[jtableTagColorIndexes[$.inArray(list[i], jtableTagNames)]];
                }
                else {
                    tagColor = 'darkgrey';
                }
                
                display += '<span class="label" style="margin-right: 5px; background-color:'+tagColor+'">' + list[i] + '</span>'

                if (i%4==0 && i!=0) {
                    display += '<hr style="margin: 2px 0 2px 0;">'
                }
            }
        
        return display;
    }

        var jtableTagColors                      = [];
        var jtableTagNames                       = [];
        var jtableTagColorIndexes                = [];

        function updateJtableTags(arrayAddTags, arrayDeleteTags, jtableTagNames, jtableTagColorIndexes){
            for(var i=0; i<arrayAddTags.length; i++) {
                jtableTagNames.push(arrayAddTags[i].tagName);
                jtableTagColorIndexes.push(arrayAddTags[i].tagColorIdx);
            }
            
            for(var i=0; i<arrayDeleteTags.length; i++) {
                var indexToBeRemoved = jtableTagNames.indexOf(arrayDeleteTags[i]);
                jtableTagNames.splice(indexToBeRemoved, 1);
                jtableTagColorIndexes.splice(indexToBeRemoved, 1);
            }
        }



        $('#CustomerTableContainer').jtable({
            title: 'Customers',
            sorting: true,
            defaultSorting: 'name DESC',

            actions: {
                
                listAction: function (postData, jtParams) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: '/api/read' + api_url('customers', jtParams),
                            type: 'GET',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                jtableTagColors        = data.jtableTagColors;
                                jtableTagNames         = data.jtableTagNames;
                                jtableTagColorIndexes  = data.jtableTagColorIndexes;
                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },
                
                createAction: function (postData, jtParams) {
                    var now = new Date().getTime();
                    postData += '&timer=' + now.toString();
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: '/api/create' + api_url('customers', jtParams),
                            type: 'POST',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                if (data.Result === 'OK')
                                    updateJtableTags(data.jtableAddTags, data.jtableDeleteTags, jtableTagNames, jtableTagColorIndexes);
                                $dfd.resolve(data);
                            },
                            error: function (data) {
                                $dfd.reject();
                            }
                        });
                    });
                },

                updateAction: function(postData, jtParams) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: '/api/update' + api_url('customers', jtParams),
                            type: 'POST',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                updateJtableTags(data.jtableAddTags, data.jtableDeleteTags, jtableTagNames, jtableTagColorIndexes);
                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },
                


                deleteAction: function(postData) {
                    return $.Deferred(function ($dfd) {
                        $.ajax({
                            url: '/api/delete' + api_url('customers'),
                            type: 'POST',
                            dataType: 'json',
                            data: postData,
                            success: function (data) {
                                updateJtableTags(data.jtableAddTags, data.jtableDeleteTags, jtableTagNames, jtableTagColorIndexes);
                                $dfd.resolve(data);
                            },
                            error: function () {
                                $dfd.reject();
                            }
                        });
                    });
                },


            },

            fields: {
                key: {
                    key: true,
                    list: false
                },
                name: {
                    title: 'Name',
                    width: '20%'

                },
                tags: {
                    sorting: false,
                    title: 'Tags',
                    width: '20%',
                    display: function(data) {
                        return listToTags(data.record.tags, true)
                    }
                },
                channels: {
                    sorting: false,
                    title: 'Channels',
                    width: '20%',
                    display: function(data) {
                        return listToTags(data.record.channels, false)
                    }
                },
                timer: {
                    create: false,
                    edit: false,
                    title: 'Latest contact',
                    width: '20%',
                    display: function(data) {
                        return '<small  class="dynamic-timer" data-start="'+data.record.timer+'"></small>' //onclick="resetTimer(\''+data.record.key+'\')"
                    }
                }
            },

            formCreated: function(event, data) {
                //data.form.find("#Edit-tags").addClass('tags')
                data.form.find("#Edit-tags").tagsInput();
                data.form.find("#Edit-channels").tagsInput();
            },

            // when row is added, add button to reset timers and update timers
            rowInserted: function(event, data) {
                $( "<td class='jtable-command-column'><button onclick=\"resetTimer(\'"  +data.record.key  + "\')\" title='Reset Timer' class='jtable-command-button jtable-reset-timer-command-button'><span>Reset Timer</span></button></td>" ).insertBefore(data.row.find( ".jtable-command-column" )[0]);
                //data.row.append( "<td class='jtable-command-column'><button onclick=\"resetTimer(\'"  +data.record.key  + "\')\" title='Reset Timer' class='jtable-command-button jtable-reset-timer-command-button'><span>Reset Timer</span></button></td>" );
                updateTimers();
            },

            rowUpdated: function (event, data) {
                updateTimers();
            }

        })


        // load table data when page is ready
        $('#CustomerTableContainer').jtable('load');
        
        // add jtable header for reset timer button (not existing in default jTable)
        $('#CustomerTableContainer table thead tr').append("<th class='jtable-command-column-header' style='width: 1%;''></th>");

        // reload table data when user click load records button
        $('#LoadRecordsButton').click(function (e) {
            e.preventDefault();
            $('#CustomerTableContainer').jtable('load', {
                search:  $('#search').val()
            });
        });

        
    });
