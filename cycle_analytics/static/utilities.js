function style_goal_indicator(div_id, check_value) {
    let base_class = "border rounded-1 text-center"
    if (check_value == 1) {
        document.getElementById(div_id).innerHTML = "&#10003;";
        document.getElementById(div_id).className = base_class + " border-success bg-success-subtle";
    }
    else {
        document.getElementById(div_id).innerHTML = "&#10006;";
        document.getElementById(div_id).className = base_class + " border-danger bg-danger-subtle";
    }

}