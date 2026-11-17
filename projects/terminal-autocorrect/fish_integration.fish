# Fish glue for terminal-autocorrect.
#
# Source this file from config.fish (the installer does this for you). It
# defines three things:
#   1. fish_command_not_found - corrects unknown command tokens
#   2. sudo                  - applies the same rules to sudo's target
#   3. fish_postexec handler - records commands the user actually runs

set -g __ac_dir (path resolve (path dirname (status filename)))
set -g __ac_script "$__ac_dir/autocorrect.sh"

# Fish builtins are not in PATH, so pass them as extra candidates. They are
# only suggestions unless they are also in the cache or common-command list.
function __ac_query --no-scope-shadowing
    set -lx AC_EXTRA_CANDIDATES (builtin -n | string join ' ')
    bash "$__ac_script" $argv
end

function __ac_command_exists --no-scope-shadowing
    set -l name "$argv[1]"
    if builtin -n | string match -q -- "$name"
        return 0
    end
    if functions -q -- "$name"
        return 0
    end
    if command -s -- "$name" >/dev/null
        return 0
    end
    return 1
end

function __ac_show_suggestions --no-scope-shadowing
    echo "Did you mean: "(string join ', ' $argv) >&2
end

# Never invoke a name we cannot resolve: that would cause a correction loop.
function __ac_run_corrected --no-scope-shadowing
    set -l cmd "$argv[1]"
    set -l rest $argv[2..-1]
    if __ac_command_exists "$cmd"
        $cmd $rest
    else
        __fish_default_command_not_found_handler $cmd $rest
    end
end

# Refresh the recent-command cache once per shell. The bash helper uses
# flock, so this is safe even if several shells start at the same time.
bash "$__ac_script" cache ensure >/dev/null 2>&1

function fish_command_not_found
    set -l result (__ac_query check $argv)
    if test (count $result) -eq 0
        __fish_default_command_not_found_handler $argv
        return
    end

    set -l fields (string split \t $result[1])
    switch $fields[1]
        case RUN
            __ac_run_corrected $fields[2] $argv[2..-1]
        case SUGGEST
            __ac_show_suggestions $fields[2..-1]
            return 1
        case NONE
            __fish_default_command_not_found_handler $argv
    end
end

# sudo itself is a real command, so fish's not-found hook never sees the
# command that follows it. This wrapper routes that target through the same
# policy and always delegates the real work to `command sudo`.
function sudo
    if test (count $argv) -eq 0; or string match -q -- '-*' "$argv[1]"
        command sudo $argv
        return $status
    end

    set -l target "$argv[1]"
    if __ac_command_exists "$target"
        command sudo $argv
        return $status
    end

    set -l result (__ac_query sudo "$target")
    if test (count $result) -eq 0
        command sudo $argv
        return $status
    end

    set -l fields (string split \t $result[1])
    switch $fields[1]
        case RUN
            set -l rest $argv[2..-1]
            command sudo $fields[2] $rest
        case SUGGEST
            __ac_show_suggestions $fields[2..-1]
            return 1
        case NONE
            command sudo $argv
    end
end

# Every command the user runs is recorded, making it trusted for future
# one-edit corrections without waiting for a cache rebuild.
function __ac_record_command --on-event fish_postexec
    if test (count $argv) -eq 0
        return
    end
    set -l line (string join ' ' $argv)
    bash "$__ac_script" cache add-line "$line" >/dev/null 2>&1
end
