/**
 * GENERATED FILE - do not hand-edit.
 * Regenerate with: npm run generate:api-types
 *
 * Source: backend/openapi/openapi.json
 * Generated: 2026-11-28T11:25:22.064Z
 */
export interface paths {
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/totp": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login Totp */
        post: operations["login_totp_api_v1_auth_login_totp_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/passkey/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Options */
        post: operations["passkey_options_api_v1_auth_login_passkey_options_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/passkey": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login Passkey */
        post: operations["login_passkey_api_v1_auth_login_passkey_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Me */
        get: operations["read_me_api_v1_web_users_me_get"];
        put?: never;
        post?: never;
        /**
         * Delete Own Account
         * @description Deletes the own account terminally after re-authentication (password
         *     or passkey assertion) and the typed e-mail address, and ends the session.
         */
        delete: operations["delete_own_account_api_v1_web_users_me_delete"];
        options?: never;
        head?: never;
        /** Update Me */
        patch: operations["update_me_api_v1_web_users_me_patch"];
        trace?: never;
    };
    "/api/v1/web/users/me/avatar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Replace Avatar
         * @description Sets the avatar to the uploaded image, replacing and deleting the
         *     previous one. Images only; 413 when too large, 415 for other types.
         */
        put: operations["replace_avatar_api_v1_web_users_me_avatar_put"];
        post?: never;
        /**
         * Remove Avatar
         * @description Removes the avatar and deletes its file; the initials show again.
         */
        delete: operations["remove_avatar_api_v1_web_users_me_avatar_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["change_password_api_v1_web_users_me_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/totp/enroll": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Enroll Totp */
        post: operations["enroll_totp_api_v1_web_users_me_totp_enroll_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/totp/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Totp */
        post: operations["confirm_totp_api_v1_web_users_me_totp_confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/totp/disable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Disable Totp */
        post: operations["disable_totp_api_v1_web_users_me_totp_disable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/passkeys": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Passkeys */
        get: operations["list_passkeys_api_v1_web_users_me_passkeys_get"];
        put?: never;
        /** Register Passkey */
        post: operations["register_passkey_api_v1_web_users_me_passkeys_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/passkeys/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Passkey Registration Options */
        post: operations["passkey_registration_options_api_v1_web_users_me_passkeys_options_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/passkeys/{passkey_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Passkey */
        delete: operations["remove_passkey_api_v1_web_users_me_passkeys__passkey_id__delete"];
        options?: never;
        head?: never;
        /** Rename Passkey */
        patch: operations["rename_passkey_api_v1_web_users_me_passkeys__passkey_id__patch"];
        trace?: never;
    };
    "/api/v1/web/users/me/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sessions */
        get: operations["list_sessions_api_v1_web_users_me_sessions_get"];
        put?: never;
        post?: never;
        /** Revoke Other Sessions */
        delete: operations["revoke_other_sessions_api_v1_web_users_me_sessions_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/sessions/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Current Session */
        get: operations["read_current_session_api_v1_web_users_me_sessions_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Session */
        delete: operations["revoke_session_api_v1_web_users_me_sessions__session_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/trusted-devices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Trusted Devices */
        get: operations["list_trusted_devices_api_v1_web_users_me_trusted_devices_get"];
        put?: never;
        post?: never;
        /** Revoke All Trusted Devices */
        delete: operations["revoke_all_trusted_devices_api_v1_web_users_me_trusted_devices_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/trusted-devices/{device_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Trusted Device */
        delete: operations["revoke_trusted_device_api_v1_web_users_me_trusted_devices__device_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/personal-access-tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Pats */
        get: operations["list_pats_api_v1_web_users_me_personal_access_tokens_get"];
        put?: never;
        /** Create Pat */
        post: operations["create_pat_api_v1_web_users_me_personal_access_tokens_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/personal-access-tokens/{token_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Pat */
        delete: operations["revoke_pat_api_v1_web_users_me_personal_access_tokens__token_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/security-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Own Security Events */
        get: operations["list_own_security_events_api_v1_web_users_me_security_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/agent-calls/tools": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Own Agent Call Tools
         * @description The tool names in the user's own agent call log.
         */
        get: operations["list_own_agent_call_tools_api_v1_web_users_me_agent_calls_tools_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/agent-calls": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Own Agent Calls
         * @description The tool calls the user's agents made with the user's tokens.
         */
        get: operations["list_own_agent_calls_api_v1_web_users_me_agent_calls_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/features": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Features */
        get: operations["read_features_api_v1_web_settings_features_get"];
        /** Save Features */
        put: operations["save_features_api_v1_web_settings_features_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/retention": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Retention */
        get: operations["read_retention_api_v1_web_settings_retention_get"];
        /** Save Retention */
        put: operations["save_retention_api_v1_web_settings_retention_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/backup-retention": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Backup Retention
         * @description How long the nightly dumps keep deleted data, for every signed-in
         *     user, since the deletion dialogs name it.
         */
        get: operations["read_backup_retention_api_v1_web_settings_backup_retention_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/maintenance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Maintenance */
        get: operations["read_maintenance_api_v1_web_settings_maintenance_get"];
        /**
         * Save Maintenance
         * @description Stays writable while maintenance is on, so it can be switched off.
         */
        put: operations["save_maintenance_api_v1_web_settings_maintenance_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Alerts */
        get: operations["list_alerts_api_v1_web_settings_mail_alerts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Mail Templates */
        get: operations["list_mail_templates_api_v1_web_settings_mail_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Save Mail Templates
         * @description Saves the given languages; a blank body returns to the default.
         */
        put: operations["save_mail_templates_api_v1_web_settings_mail_templates__kind__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates/{kind}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview Mail Template
         * @description Renders a draft with the kind's sample values, exactly as it is sent.
         */
        post: operations["preview_mail_template_api_v1_web_settings_mail_templates__kind__preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates/{kind}/default": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Default Mail Template */
        get: operations["default_mail_template_api_v1_web_settings_mail_templates__kind__default_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates/{kind}/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Mail Template
         * @description Saves an HTML template file for one language; its <title> is the subject.
         */
        post: operations["import_mail_template_api_v1_web_settings_mail_templates__kind__import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/templates/{kind}/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Mail Template */
        get: operations["export_mail_template_api_v1_web_settings_mail_templates__kind__export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/backups/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Back Up Now
         * @description Asks the backup sidecar for a dump now; it starts within seconds.
         *     409 while a request is still waiting, 503 without the sidecar.
         */
        post: operations["back_up_now_api_v1_web_admin_backups_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/backups/restore-guidance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Restore Guidance */
        get: operations["read_restore_guidance_api_v1_web_admin_backups_restore_guidance_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Logs
         * @description The recent warnings and errors of the backend worker that answers,
         *     with secrets redacted.
         */
        get: operations["read_logs_api_v1_web_admin_logs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/legal/{kind}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Legal Versions */
        get: operations["list_legal_versions_api_v1_web_admin_legal__kind__versions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/legal/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Publish Legal Page
         * @description Publishes the next version. A new privacy statement version asks
         *     every user to acknowledge it again.
         */
        post: operations["publish_legal_page_api_v1_web_admin_legal__kind__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/legal/privacy/draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Privacy Statement Draft
         * @description A draft written from this instance's configuration, to edit and
         *     publish. `{{ privacy_mode }}` marks where the privacy mode section goes.
         */
        get: operations["privacy_statement_draft_api_v1_web_admin_legal_privacy_draft_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/legal/privacy/acknowledgements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Privacy Acknowledgements
         * @description Which person acknowledged which privacy statement version: those on
         *     the current version, and those still asked with the version they
         *     acknowledged last.
         */
        get: operations["privacy_acknowledgements_api_v1_web_admin_legal_privacy_acknowledgements_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/privacy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Own Privacy Status */
        get: operations["own_privacy_status_api_v1_web_users_me_privacy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/privacy/acknowledge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Acknowledge Privacy
         * @description 409 when the version is not the current one any more.
         */
        post: operations["acknowledge_privacy_api_v1_web_users_me_privacy_acknowledge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/privacy/decline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Decline Privacy
         * @description Declining signs the user out; they are asked again at the next login.
         */
        post: operations["decline_privacy_api_v1_web_users_me_privacy_decline_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/consents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Own Consents */
        get: operations["own_consents_api_v1_web_users_me_consents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/consents/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Grant Consent */
        put: operations["grant_consent_api_v1_web_users_me_consents__kind__put"];
        post?: never;
        /**
         * Withdraw Consent
         * @description Withdrawing ai_agents revokes the user's agent tokens; withdrawing
         *     health_data deletes their allergies, intolerances and diets.
         */
        delete: operations["withdraw_consent_api_v1_web_users_me_consents__kind__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/cook-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Cooking Calendar
         * @description Everyone's cook events in a date range, at most 400 days.
         */
        get: operations["cooking_calendar_api_v1_web_cook_events_get"];
        put?: never;
        /**
         * Create Cook Event
         * @description "I cooked this": records the viewer cooking a recipe on a day. A
         *     second log of the same recipe on the same day answers 409
         *     CookEventExistsError.
         */
        post: operations["create_cook_event_api_v1_web_cook_events_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/cook-events/recent": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recent Cook Events */
        get: operations["recent_cook_events_api_v1_web_cook_events_recent_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/cook-events/on-this-day": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * On This Day
         * @description What was cooked around this day in earlier years.
         */
        get: operations["on_this_day_api_v1_web_cook_events_on_this_day_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/cook-events/once": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Log Cook Once
         * @description Logs the recipe as cooked on the day unless the viewer already did;
         *     repeating it changes nothing. Cook mode calls it when the cook
         *     finishes.
         */
        put: operations["log_cook_once_api_v1_web_cook_events_once_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/cook-events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Cook Event */
        put: operations["update_cook_event_api_v1_web_cook_events__event_id__put"];
        post?: never;
        /** Delete Cook Event */
        delete: operations["delete_cook_event_api_v1_web_cook_events__event_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/meal-plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Meal Plan
         * @description The planned meals of one plan in a range of at most 62 days: the
         *     household's for a member and the viewer's personal plan otherwise,
         *     unless `scope` names one.
         */
        get: operations["read_meal_plan_api_v1_web_meal_plan_get"];
        put?: never;
        /** Add Meal */
        post: operations["add_meal_api_v1_web_meal_plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/meal-plan/suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Suggest Meals
         * @description Published recipes worth planning in the range of one plan, best
         *     first, each with the reason that carried it. Ranked from the plan's
         *     cooking history (every member's for the household's plan, the viewer's
         *     own for the personal one), favourites, the season and, with `slot`, the
         *     meal tags; recipes already planned in the range are left out.
         */
        get: operations["suggest_meals_api_v1_web_meal_plan_suggestions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/meal-plan/{entry_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Meal */
        put: operations["update_meal_api_v1_web_meal_plan__entry_id__put"];
        post?: never;
        /** Delete Meal */
        delete: operations["delete_meal_api_v1_web_meal_plan__entry_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/meal-plan/shopping-list": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Meal Plan To Shopping List
         * @description Puts every planned recipe of the range on a shopping list, each
         *     scaled to its planned servings.
         */
        post: operations["meal_plan_to_shopping_list_api_v1_web_meal_plan_shopping_list_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/home": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Home
         * @description The start page: the food fact of the day, what was cooked on this day in earlier years, what
         *     everyone cooked lately, the viewer's favourites, the newest recipes and
         *     recipes in season this month.
         */
        get: operations["home_api_v1_web_home_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/food-restrictions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Food Restrictions
         * @description The viewer's own allergies and intolerances. There is no way to read
         *     another user's.
         */
        get: operations["list_food_restrictions_api_v1_web_users_me_food_restrictions_get"];
        put?: never;
        /** Add Food Restriction */
        post: operations["add_food_restriction_api_v1_web_users_me_food_restrictions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/food-restrictions/{restriction_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Food Restriction */
        delete: operations["remove_food_restriction_api_v1_web_users_me_food_restrictions__restriction_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Own Data
         * @description Download my data: the profile, consents and every cookbook record
         *     of the signed-in user as one JSON file.
         */
        get: operations["export_own_data_api_v1_web_users_me_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Own Deletion Impact
         * @description What deleting the own account would do, for the confirmation dialog.
         */
        get: operations["own_deletion_impact_api_v1_web_users_me_deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/{user_id}/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Account Deletion Impact */
        get: operations["account_deletion_impact_api_v1_web_users__user_id__deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read User */
        get: operations["read_user_api_v1_web_users__user_id__get"];
        put?: never;
        post?: never;
        /**
         * Delete User
         * @description Deletes the account terminally and without a trace.
         */
        delete: operations["delete_user_api_v1_web_users__user_id__delete"];
        options?: never;
        head?: never;
        /** Update User */
        patch: operations["update_user_api_v1_web_users__user_id__patch"];
        trace?: never;
    };
    "/api/v1/web/users/directory": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * User Directory
         * @description Names and avatars of the active accounts, for every signed-in user, so
         *     recipes can show who wrote them and pickers can show whom they offer.
         */
        get: operations["user_directory_api_v1_web_users_directory_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Users
         * @description Every account by name, or one page of them with `limit` and `offset`.
         */
        get: operations["list_users_api_v1_web_users_get"];
        put?: never;
        /** Create User */
        post: operations["create_user_api_v1_web_users_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/{user_id}/reset-totp": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset User Totp */
        post: operations["reset_user_totp_api_v1_web_users__user_id__reset_totp_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/{user_id}/avatar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Replace User Avatar
         * @description Sets the user's avatar to the uploaded image, replacing and deleting
         *     the previous one. Images only; 413 when too large, 415 for other types.
         */
        put: operations["replace_user_avatar_api_v1_web_users__user_id__avatar_put"];
        post?: never;
        /**
         * Remove User Avatar
         * @description Removes the user's avatar and deletes its file.
         */
        delete: operations["remove_user_avatar_api_v1_web_users__user_id__avatar_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/{user_id}/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Force Logout User */
        post: operations["force_logout_user_api_v1_web_users__user_id__logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/permissions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Permissions */
        get: operations["list_permissions_api_v1_web_permissions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/groups/directory": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Group Directory
         * @description Every group by id and name, for any signed-in user, so recipes can be
         *     shared with a group without the right to manage groups.
         */
        get: operations["group_directory_api_v1_web_groups_directory_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/groups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Groups */
        get: operations["list_groups_api_v1_web_groups_get"];
        put?: never;
        /** Create Group */
        post: operations["create_group_api_v1_web_groups_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/groups/{group_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Group */
        delete: operations["delete_group_api_v1_web_groups__group_id__delete"];
        options?: never;
        head?: never;
        /** Update Group */
        patch: operations["update_group_api_v1_web_groups__group_id__patch"];
        trace?: never;
    };
    "/api/v1/web/api-keys": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Api Keys */
        get: operations["list_api_keys_api_v1_web_api_keys_get"];
        put?: never;
        /** Create Api Key */
        post: operations["create_api_key_api_v1_web_api_keys_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/api-keys/{key_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Api Key */
        delete: operations["revoke_api_key_api_v1_web_api_keys__key_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/security-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Security Events */
        get: operations["list_security_events_api_v1_web_security_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/agent-calls": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Agent Calls
         * @description Every agent tool call on the instance.
         */
        get: operations["list_agent_calls_api_v1_web_agent_calls_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/agent-calls/tools": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Agent Call Tools
         * @description The tool names in the whole log, for the table's filter.
         */
        get: operations["list_agent_call_tools_api_v1_web_agent_calls_tools_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/general": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read General */
        get: operations["read_general_api_v1_web_settings_general_get"];
        /** Save General */
        put: operations["save_general_api_v1_web_settings_general_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/security": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Security */
        get: operations["read_security_api_v1_web_settings_security_get"];
        /** Save Security */
        put: operations["save_security_api_v1_web_settings_security_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Mail */
        get: operations["read_mail_api_v1_web_settings_mail_get"];
        /** Save Mail */
        put: operations["save_mail_api_v1_web_settings_mail_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/mail/test": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send Test Mail
         * @description Sends the test mail template, to `to` or the acting user's own address.
         */
        post: operations["send_test_mail_api_v1_web_settings_mail_test_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/integrations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Integrations */
        get: operations["read_integrations_api_v1_web_settings_integrations_get"];
        /** Save Integrations */
        put: operations["save_integrations_api_v1_web_settings_integrations_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/agents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Agents */
        get: operations["read_agents_api_v1_web_settings_agents_get"];
        /** Save Agents */
        put: operations["save_agents_api_v1_web_settings_agents_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/privacy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Privacy
         * @description Every signed-in user reads it, since the recipe editor needs to know
         *     whether visibility can be chosen.
         */
        get: operations["read_privacy_api_v1_web_settings_privacy_get"];
        /** Save Privacy */
        put: operations["save_privacy_api_v1_web_settings_privacy_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/shopping": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Shopping */
        get: operations["read_shopping_api_v1_web_settings_shopping_get"];
        /**
         * Save Shopping
         * @description The recently bought window of continuous lists and the idle days
         *     after which a normal list deletes itself.
         */
        put: operations["save_shopping_api_v1_web_settings_shopping_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Notifications */
        get: operations["read_notifications_api_v1_web_settings_notifications_get"];
        /** Save Notifications */
        put: operations["save_notifications_api_v1_web_settings_notifications_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/settings/banner": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Banner */
        get: operations["read_banner_api_v1_web_settings_banner_get"];
        /** Save Banner */
        put: operations["save_banner_api_v1_web_settings_banner_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/host": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Host */
        get: operations["read_host_api_v1_web_admin_host_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/storage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Storage */
        get: operations["read_storage_api_v1_web_admin_storage_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Webhook Events */
        get: operations["list_webhook_events_api_v1_web_admin_webhooks_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Webhooks */
        get: operations["list_webhooks_api_v1_web_admin_webhooks_get"];
        put?: never;
        /** Create Webhook */
        post: operations["create_webhook_api_v1_web_admin_webhooks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/{webhook_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Webhook */
        get: operations["read_webhook_api_v1_web_admin_webhooks__webhook_id__get"];
        /** Update Webhook */
        put: operations["update_webhook_api_v1_web_admin_webhooks__webhook_id__put"];
        post?: never;
        /** Delete Webhook */
        delete: operations["delete_webhook_api_v1_web_admin_webhooks__webhook_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/{webhook_id}/rotate-secret": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rotate Webhook Secret */
        post: operations["rotate_webhook_secret_api_v1_web_admin_webhooks__webhook_id__rotate_secret_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/{webhook_id}/test": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Test Webhook
         * @description Sends a `ping` now and answers its logged delivery.
         */
        post: operations["test_webhook_api_v1_web_admin_webhooks__webhook_id__test_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/{webhook_id}/deliveries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Webhook Deliveries */
        get: operations["list_webhook_deliveries_api_v1_web_admin_webhooks__webhook_id__deliveries_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/webhooks/{webhook_id}/deliveries/{delivery_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Webhook Delivery */
        post: operations["retry_webhook_delivery_api_v1_web_admin_webhooks__webhook_id__deliveries__delivery_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/notices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notices */
        get: operations["list_notices_api_v1_web_admin_notices_get"];
        put?: never;
        /** Create Notice */
        post: operations["create_notice_api_v1_web_admin_notices_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/notices/{notice_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Notice */
        put: operations["update_notice_api_v1_web_admin_notices__notice_id__put"];
        post?: never;
        /** Delete Notice */
        delete: operations["delete_notice_api_v1_web_admin_notices__notice_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/notices/{notice_id}/acknowledgements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Notice Acknowledgements */
        get: operations["notice_acknowledgements_api_v1_web_admin_notices__notice_id__acknowledgements_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/notices/pending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Pending Notices
         * @description Active notices the user has not acknowledged, oldest first, in the
         *     requested locale (default: the user's own language).
         */
        get: operations["pending_notices_api_v1_web_notices_pending_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/notices/{notice_id}/acknowledge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Acknowledge Notice */
        post: operations["acknowledge_notice_api_v1_web_notices__notice_id__acknowledge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/self": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Own Instance */
        get: operations["read_own_instance_api_v1_web_admin_peers_self_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/invitations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Peer Invitations */
        get: operations["list_peer_invitations_api_v1_web_admin_peers_invitations_get"];
        put?: never;
        /** Create Peer Invitation */
        post: operations["create_peer_invitation_api_v1_web_admin_peers_invitations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/invitations/{invitation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Peer Invitation */
        delete: operations["revoke_peer_invitation_api_v1_web_admin_peers_invitations__invitation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Peer Invitation */
        post: operations["accept_peer_invitation_api_v1_web_admin_peers_accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Peers */
        get: operations["list_peers_api_v1_web_admin_peers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/switches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Peer Switches */
        put: operations["update_peer_switches_api_v1_web_admin_peers__peer_id__switches_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Peer */
        post: operations["refresh_peer_api_v1_web_admin_peers__peer_id__refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Peer */
        post: operations["revoke_peer_api_v1_web_admin_peers__peer_id__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Sync Peer
         * @description Sync now: the channel worker catches up with the peer and retries
         *     pending deliveries within seconds instead of at their scheduled time.
         */
        post: operations["sync_peer_api_v1_web_admin_peers__peer_id__sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/files": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload File */
        post: operations["upload_file_api_v1_web_files_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/files/{file_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read File */
        get: operations["read_file_api_v1_web_files__file_id__get"];
        put?: never;
        post?: never;
        /** Delete File */
        delete: operations["delete_file_api_v1_web_files__file_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/files/{file_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read File Content */
        get: operations["read_file_content_api_v1_web_files__file_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/resources/usage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Resource Usage */
        get: operations["resource_usage_api_v1_web_resources_usage_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/units": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Units */
        get: operations["list_units_api_v1_web_units_get"];
        put?: never;
        /** Create Unit */
        post: operations["create_unit_api_v1_web_units_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/units/{unit_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Unit */
        put: operations["update_unit_api_v1_web_units__unit_id__put"];
        post?: never;
        /** Delete Unit */
        delete: operations["delete_unit_api_v1_web_units__unit_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/units/{unit_id}/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Unit Deletion Impact */
        get: operations["unit_deletion_impact_api_v1_web_units__unit_id__deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/units/{unit_id}/merge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Merge Unit
         * @description Moves every use of the unit to the target and deletes it.
         */
        post: operations["merge_unit_api_v1_web_units__unit_id__merge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tags */
        get: operations["list_tags_api_v1_web_tags_get"];
        put?: never;
        /** Create Tag */
        post: operations["create_tag_api_v1_web_tags_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/tags/{tag_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Tag */
        put: operations["update_tag_api_v1_web_tags__tag_id__put"];
        post?: never;
        /** Delete Tag */
        delete: operations["delete_tag_api_v1_web_tags__tag_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredient-families": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Families */
        get: operations["list_families_api_v1_web_ingredient_families_get"];
        put?: never;
        /** Create Family */
        post: operations["create_family_api_v1_web_ingredient_families_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredient-families/{family_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Family */
        put: operations["update_family_api_v1_web_ingredient_families__family_id__put"];
        post?: never;
        /**
         * Delete Family
         * @description Its ingredients stay, without a family.
         */
        delete: operations["delete_family_api_v1_web_ingredient_families__family_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredient-categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Categories */
        get: operations["list_categories_api_v1_web_ingredient_categories_get"];
        put?: never;
        /** Create Category */
        post: operations["create_category_api_v1_web_ingredient_categories_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredient-categories/{category_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Category */
        put: operations["update_category_api_v1_web_ingredient_categories__category_id__put"];
        post?: never;
        /**
         * Delete Category
         * @description Ingredients move to the replacement or to none; shopping items of
         *     the category fall into "Other".
         */
        delete: operations["delete_category_api_v1_web_ingredient_categories__category_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/nutrition/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Nutrition Sources */
        get: operations["nutrition_sources_api_v1_web_nutrition_sources_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/reference-updates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Reference Updates
         * @description Overridden seed updates, allergens and diet markers first. Every
         *     other seed update was applied at start-up.
         */
        get: operations["list_reference_updates_api_v1_web_admin_reference_updates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/reference-updates/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept Reference Update
         * @description Writes the seed's value into the field; 404 when the field holds no
         *     overridden update.
         */
        post: operations["accept_reference_update_api_v1_web_admin_reference_updates_accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/catalogue/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Catalogue
         * @description Every unit, tag, category and family and the active ingredients and
         *     equipment as `cuisine-catalogue-<date>.json`. Needs manage:ingredients or
         *     write:resources.
         */
        get: operations["export_catalogue_api_v1_web_admin_catalogue_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/catalogue/import/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview Catalogue Import
         * @description Per kind and entry of the file, whether it matches an entry here or
         *     is new, and for a matched entry the fields whose values differ, with the
         *     value here and the file's. Writes nothing.
         */
        post: operations["preview_catalogue_import_api_v1_web_admin_catalogue_import_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/catalogue/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Catalogue
         * @description Creates every new entry of the kinds the caller may write, active,
         *     and writes the accepted differences, all in one transaction, reporting
         *     what was created, what was changed, the kinds left out and what could
         *     not be written.
         */
        post: operations["import_catalogue_api_v1_web_admin_catalogue_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Ingredients
         * @description The catalogue, paged. `usage_count` counts the recipes the viewer may
         *     see that use the ingredient; filtering or sorting by it counts the whole
         *     catalogue, otherwise only the page is counted.
         */
        get: operations["list_ingredients_api_v1_web_ingredients_get"];
        put?: never;
        /** Create Ingredient */
        post: operations["create_ingredient_api_v1_web_ingredients_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients/duplicates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ingredient Duplicates
         * @description Ingredients that probably mean the same food as `name`: the same
         *     name or alias without case, diacritics and spacing (`exact`, which
         *     creating would refuse with 409), or one that differs by a plural ending
         *     or a letter, for "Did you mean Erdapfel?".
         */
        get: operations["ingredient_duplicates_api_v1_web_ingredients_duplicates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients/{ingredient_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Ingredient */
        get: operations["read_ingredient_api_v1_web_ingredients__ingredient_id__get"];
        /** Update Ingredient */
        put: operations["update_ingredient_api_v1_web_ingredients__ingredient_id__put"];
        post?: never;
        /** Delete Ingredient */
        delete: operations["delete_ingredient_api_v1_web_ingredients__ingredient_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients/{ingredient_id}/activate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Activate Ingredient
         * @description Marks an agent's draft ingredient as reviewed.
         */
        post: operations["activate_ingredient_api_v1_web_ingredients__ingredient_id__activate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients/{ingredient_id}/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ingredient Deletion Impact
         * @description What the deletion dialog needs. Nothing here says whether food
         *     restrictions name the ingredient.
         */
        get: operations["ingredient_deletion_impact_api_v1_web_ingredients__ingredient_id__deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/ingredients/{ingredient_id}/merge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Merge Ingredient
         * @description Repoints recipe lines, shopping items and food restrictions to the
         *     target and deletes this ingredient. Answers with the target.
         */
        post: operations["merge_ingredient_api_v1_web_ingredients__ingredient_id__merge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/nutrition/nutrients": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Extended Nutrients
         * @description The extended nutrient catalogue in display order: the keys
         *     `extended_nutrition` takes, each with its unit and label key.
         */
        get: operations["list_extended_nutrients_api_v1_web_nutrition_nutrients_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/nutrition/usda/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Usda
         * @description Generic foods from USDA FoodData Central (public domain, CC0), with
         *     nutrition per 100 g.
         */
        get: operations["search_usda_api_v1_web_nutrition_usda_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/nutrition/usda/{fdc_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Usda Food */
        get: operations["read_usda_food_api_v1_web_nutrition_usda__fdc_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Equipment
         * @description The whole catalogue (it stays small), sorted by name in the viewer's
         *     language. `search` matches names and aliases in any language.
         */
        get: operations["list_equipment_api_v1_web_equipment_get"];
        put?: never;
        /** Create Equipment */
        post: operations["create_equipment_api_v1_web_equipment_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment/duplicates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Equipment Duplicates
         * @description Equipment that probably means the same as `name`, by the rules of
         *     GET /ingredients/duplicates.
         */
        get: operations["equipment_duplicates_api_v1_web_equipment_duplicates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment/{equipment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Equipment */
        get: operations["read_equipment_api_v1_web_equipment__equipment_id__get"];
        /** Update Equipment */
        put: operations["update_equipment_api_v1_web_equipment__equipment_id__put"];
        post?: never;
        /**
         * Delete Equipment
         * @description 409 for seeded items and for items a recipe step names.
         */
        delete: operations["delete_equipment_api_v1_web_equipment__equipment_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment/{equipment_id}/activate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Activate Equipment
         * @description Marks a draft an agent created as reviewed.
         */
        post: operations["activate_equipment_api_v1_web_equipment__equipment_id__activate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment/{equipment_id}/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Equipment Deletion Impact */
        get: operations["equipment_deletion_impact_api_v1_web_equipment__equipment_id__deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/equipment/{equipment_id}/merge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Merge Equipment
         * @description Moves recipe steps and kitchens to the target, keeps this item's
         *     names as the target's aliases and deletes it. Answers with the target.
         */
        post: operations["merge_equipment_api_v1_web_equipment__equipment_id__merge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/kitchen": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Kitchen
         * @description The viewer's kitchen: the household's when they are in one.
         */
        get: operations["read_kitchen_api_v1_web_kitchen_get"];
        /**
         * Update Kitchen
         * @description Replaces the kitchen's equipment; 422 before set-up.
         */
        put: operations["update_kitchen_api_v1_web_kitchen_put"];
        post?: never;
        /**
         * Reset Kitchen
         * @description Forgets the kitchen; nothing is flagged until it is set up again.
         */
        delete: operations["reset_kitchen_api_v1_web_kitchen_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/kitchen/setup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Set Up Kitchen
         * @description Sets the kitchen up (or starts it over) with the given items, or
         *     with the catalogue's basic items when `equipment_ids` is null. From
         *     then on recipes carry `missing_equipment` and `kitchen_ready`.
         */
        post: operations["set_up_kitchen_api_v1_web_kitchen_setup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Recipe
         * @description The recipe with its visible sub-recipes and variations, the catalogue
         *     entries they use and their images, as a `.cui` file. Allowed for anyone
         *     who can open the recipe; 404 for a recipe the caller may not see.
         */
        get: operations["export_recipe_api_v1_web_recipes__recipe_id__export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/recipes/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Recipes
         * @description The recipes with their visible sub-recipes, the catalogue entries
         *     they use and their images, as one `.cui` file for another instance.
         */
        get: operations["export_recipes_api_v1_web_admin_recipes_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/import/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview Import
         * @description The recipes of the file, each with the caller's earlier import of it,
         *     so the caller can choose per recipe to update it or to import a new
         *     copy. Checks the file like the import and stores nothing.
         */
        post: operations["preview_import_api_v1_web_recipes_import_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Recipes
         * @description Imports every recipe of the file as a draft of the caller, or as an
         *     update of the caller's earlier import where asked, and reports what
         *     matched, what was created and what could not be placed.
         */
        post: operations["import_recipes_api_v1_web_recipes_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Recipes */
        get: operations["list_recipes_api_v1_web_recipes_get"];
        put?: never;
        /**
         * Create Recipe
         * @description Creates the recipe as a draft.
         */
        post: operations["create_recipe_api_v1_web_recipes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/step-images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Step Images
         * @description The step image library for the editor: one entry per image that a
         *     step of a recipe the viewer may see shows, mirrors left out. Unknown
         *     ingredient and equipment ids are ignored, since they only rank.
         */
        get: operations["list_step_images_api_v1_web_step_images_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Recipe
         * @description The recipe in the viewer's language, its amounts scaled to `servings`
         *     (the recipe's own servings by default), with nutrition, allergens and
         *     the viewer's own warnings, favourite, rating and note.
         */
        get: operations["read_recipe_api_v1_web_recipes__recipe_id__get"];
        /** Update Recipe */
        put: operations["update_recipe_api_v1_web_recipes__recipe_id__put"];
        post?: never;
        /** Delete Recipe */
        delete: operations["delete_recipe_api_v1_web_recipes__recipe_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Recipe For Editing */
        get: operations["read_recipe_for_editing_api_v1_web_recipes__recipe_id__edit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/translation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Save Recipe Translation
         * @description Adds or replaces one language of the recipe.
         */
        put: operations["save_recipe_translation_api_v1_web_recipes__recipe_id__translation_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish Recipe */
        post: operations["publish_recipe_api_v1_web_recipes__recipe_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/unpublish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Unpublish Recipe */
        post: operations["unpublish_recipe_api_v1_web_recipes__recipe_id__unpublish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/deletion-impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Recipe Deletion Impact
         * @description Whether the recipe can be deleted: recipes using it as a sub-recipe
         *     block it; the dialog lists those the viewer can see.
         */
        get: operations["recipe_deletion_impact_api_v1_web_recipes__recipe_id__deletion_impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/favourite": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Favourite */
        put: operations["set_favourite_api_v1_web_recipes__recipe_id__favourite_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/rating": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Rate Recipe
         * @description Rates the recipe, or with `variation_id` one of its variations; the
         *     average and count answered are of what was rated.
         */
        put: operations["rate_recipe_api_v1_web_recipes__recipe_id__rating_put"];
        post?: never;
        /**
         * Remove Rating
         * @description Removes the viewer's rating and answers with the new average.
         */
        delete: operations["remove_rating_api_v1_web_recipes__recipe_id__rating_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Save Note
         * @description The viewer's private note; nobody else ever sees it. An empty text
         *     deletes it.
         */
        put: operations["save_note_api_v1_web_recipes__recipe_id__note_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/cook-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Recipe Cook Events
         * @description Who cooked this recipe when, newest first, at most `limit` of them.
         */
        get: operations["recipe_cook_events_api_v1_web_recipes__recipe_id__cook_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Recipe Revisions
         * @description The recipe's history, newest first; for whoever may edit it.
         */
        get: operations["list_recipe_revisions_api_v1_web_recipes__recipe_id__revisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/revisions/{number}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Recipe Revision */
        get: operations["read_recipe_revision_api_v1_web_recipes__recipe_id__revisions__number__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/revisions/{number}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Restore Recipe Revision
         * @description Makes the revision's content the current recipe and records a
         *     `restored` revision; the status and visibility stay. 409
         *     `RevisionRestoreError` names an ingredient, unit, tag, equipment item
         *     or sub-recipe that no longer exists; vanished images are dropped.
         */
        post: operations["restore_recipe_revision_api_v1_web_recipes__recipe_id__revisions__number__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/variations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Variations
         * @description The variations of the recipe the viewer may see, oldest first: every
         *     shared one and the viewer's own private ones.
         */
        get: operations["list_variations_api_v1_web_recipes__recipe_id__variations_get"];
        put?: never;
        /**
         * Create Variation
         * @description Adds a variation to a recipe the actor can see. 422
         *     `InvalidVariationError` when a change names a step or line the recipe
         *     lacks; 422 `InvalidMentionError` for a mention outside its step.
         */
        post: operations["create_variation_api_v1_web_recipes__recipe_id__variations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/variations/{variation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Variation */
        get: operations["read_variation_api_v1_web_recipes__recipe_id__variations__variation_id__get"];
        /**
         * Update Variation
         * @description Replaces the variation as a whole; its author only. The step numbers
         *     refer to the recipe as it is now, and the variation moves onto the
         *     recipe's latest revision.
         */
        put: operations["update_variation_api_v1_web_recipes__recipe_id__variations__variation_id__put"];
        post?: never;
        /**
         * Delete Variation
         * @description Its author, or manage:recipes.
         */
        delete: operations["delete_variation_api_v1_web_recipes__recipe_id__variations__variation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/variations/{variation_id}/view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * View Variation
         * @description The recipe with the variation applied, in the shape of the recipe
         *     detail, everything derived from the applied recipe, plus a marker per
         *     step for what differs.
         */
        get: operations["view_variation_api_v1_web_recipes__recipe_id__variations__variation_id__view_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/variations/{variation_id}/adopt": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Adopt Variation
         * @description Writes all changes (`change_ids` null) or the chosen ones into the
         *     original as an `adopted` revision crediting the variation's author; the
         *     recipe's editors only. The adopted changes leave the variation.
         */
        post: operations["adopt_variation_api_v1_web_recipes__recipe_id__variations__variation_id__adopt_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/co-editors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Co Editors
         * @description For whoever may edit the recipe.
         */
        get: operations["list_co_editors_api_v1_web_recipes__recipe_id__co_editors_get"];
        /**
         * Set Co Editors
         * @description Replaces the co-editors; the owner only (403 otherwise). 422
         *     `CoEditorError` for the owner, an inactive or service account, or
         *     someone who cannot see the recipe.
         */
        put: operations["set_co_editors_api_v1_web_recipes__recipe_id__co_editors_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/copy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Copy Recipe
         * @description "Copy as my recipe": an independent draft of the actor's, linked to
         *     the original (`based_on`).
         */
        post: operations["copy_recipe_api_v1_web_recipes__recipe_id__copy_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/recipes/{recipe_id}/copies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Copies
         * @description The copies of the recipe the viewer may see, newest first.
         */
        get: operations["list_copies_api_v1_web_recipes__recipe_id__copies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/peers/share-targets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Peer Share Targets */
        get: operations["list_peer_share_targets_api_v1_web_peers_share_targets_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/incoming-recipes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Incoming Recipes */
        get: operations["list_incoming_recipes_api_v1_web_admin_incoming_recipes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/incoming-recipes/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Incoming Recipe */
        get: operations["read_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/incoming-recipes/{item_id}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Incoming Recipe */
        post: operations["accept_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/incoming-recipes/{item_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Incoming Recipe */
        post: operations["reject_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/incoming-recipes/{item_id}/reopen": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reopen Incoming Recipe */
        post: operations["reopen_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__reopen_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/incoming-recipes/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Waiting Recipes */
        post: operations["accept_waiting_recipes_api_v1_web_admin_peers__peer_id__incoming_recipes_accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/mappings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Peer Mappings */
        get: operations["list_peer_mappings_api_v1_web_admin_peers__peer_id__mappings_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peers/{peer_id}/mappings/{kind}/{source_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Correct Peer Mapping */
        put: operations["correct_peer_mapping_api_v1_web_admin_peers__peer_id__mappings__kind___source_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peer-suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Peer Suggestions */
        get: operations["list_peer_suggestions_api_v1_web_admin_peer_suggestions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peer-suggestions/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Peer Suggestion */
        post: operations["accept_peer_suggestion_api_v1_web_admin_peer_suggestions_accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/peer-suggestions/dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Peer Suggestion */
        post: operations["dismiss_peer_suggestion_api_v1_web_admin_peer_suggestions_dismiss_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Shopping Lists
         * @description The lists the viewer owns or was given.
         */
        get: operations["list_shopping_lists_api_v1_web_shopping_lists_get"];
        put?: never;
        /** Create Shopping List */
        post: operations["create_shopping_list_api_v1_web_shopping_lists_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Shopping List Notes
         * @description The viewer's notes about unused lists that deleted themselves, newest first.
         */
        get: operations["list_shopping_list_notes_api_v1_web_shopping_lists_notes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/notes/{note_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Dismiss Shopping List Note */
        delete: operations["dismiss_shopping_list_note_api_v1_web_shopping_lists_notes__note_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Shopping List */
        get: operations["read_shopping_list_api_v1_web_shopping_lists__list_id__get"];
        /**
         * Update Shopping List
         * @description Renames the list and switches its mode or keep flag; the owner also
         *     changes who it is shared with. Switching to continuous deletes the items
         *     ticked before the recently bought window.
         */
        put: operations["update_shopping_list_api_v1_web_shopping_lists__list_id__put"];
        post?: never;
        /** Delete Shopping List */
        delete: operations["delete_shopping_list_api_v1_web_shopping_lists__list_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/leave": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Leave Shopping List */
        post: operations["leave_shopping_list_api_v1_web_shopping_lists__list_id__leave_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Shopping Item
         * @description Adds an item; an amount of an ingredient joins an open item of the
         *     same ingredient and unit. Answers with the whole list.
         */
        post: operations["add_shopping_item_api_v1_web_shopping_lists__list_id__items_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Shopping Item */
        delete: operations["delete_shopping_item_api_v1_web_shopping_lists__list_id__items__item_id__delete"];
        options?: never;
        head?: never;
        /** Update Shopping Item */
        patch: operations["update_shopping_item_api_v1_web_shopping_lists__list_id__items__item_id__patch"];
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/clear-checked": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Clear Checked Items */
        post: operations["clear_checked_items_api_v1_web_shopping_lists__list_id__clear_checked_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/recipes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Recipe To List
         * @description Adds a recipe's ingredients for `servings` (its own by default).
         */
        post: operations["add_recipe_to_list_api_v1_web_shopping_lists__list_id__recipes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/shopping-lists/{list_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Shopping List Events
         * @description Server-sent events of one list: `ready` once connected, then
         *     `change` whenever someone changes the list. A client refetches the list
         *     on every change and after every reconnect.
         */
        get: operations["shopping_list_events_api_v1_web_shopping_lists__list_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/mine": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** My Household */
        get: operations["my_household_api_v1_web_households_mine_get"];
        /** Rename Household */
        put: operations["rename_household_api_v1_web_households_mine_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Household
         * @description Founds a household with the viewer as its first member and creates
         *     its default shopping list.
         */
        post: operations["create_household_api_v1_web_households_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/mine/leave": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Leave Household
         * @description The last member leaving dissolves the household with its plan and
         *     default list.
         */
        post: operations["leave_household_api_v1_web_households_mine_leave_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/mine/invitations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Invite To Household */
        post: operations["invite_to_household_api_v1_web_households_mine_invitations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/mine/invitations/{invitation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Invitation */
        delete: operations["revoke_invitation_api_v1_web_households_mine_invitations__invitation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/invitations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * My Invitations
         * @description The invitations the viewer received.
         */
        get: operations["my_invitations_api_v1_web_households_invitations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/invitations/{invitation_id}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Invitation */
        post: operations["accept_invitation_api_v1_web_households_invitations__invitation_id__accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/households/invitations/{invitation_id}/decline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decline Invitation */
        post: operations["decline_invitation_api_v1_web_households_invitations__invitation_id__decline_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/admin/households": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Household Memberships
         * @description Who belongs to which household, for user administration. Never the
         *     households' plans or lists.
         */
        get: operations["household_memberships_api_v1_web_admin_households_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/resolve/{public_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Resolve Public Id */
        get: operations["resolve_public_id_api_v1_web_resolve__public_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/oauth/authorize/inspect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Inspect Authorization */
        post: operations["inspect_authorization_api_v1_web_oauth_authorize_inspect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/oauth/authorize/decision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide Authorization */
        post: operations["decide_authorization_api_v1_web_oauth_authorize_decision_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/connected-apps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Connected Apps */
        get: operations["list_connected_apps_api_v1_web_users_me_connected_apps_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/web/users/me/connected-apps/{app_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Revoke Connected App */
        delete: operations["revoke_connected_app_api_v1_web_users_me_connected_apps__app_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/info": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Public Info */
        get: operations["public_info_api_v1_public_info_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/robots.txt": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Public Robots
         * @description The robots.txt of the instance, which the frontend serves at
         *     /robots.txt: everything closed, unless the administrator lets search
         *     engines index the public recipes while they are allowed.
         */
        get: operations["public_robots_api_v1_public_robots_txt_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/manifest.webmanifest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Public Manifest
         * @description The web app manifest, so the instance installs under its own name, in
         *     its default language and with its accent colour. index.html links it
         *     here, below /api, so it needs no route of its own in front of the app.
         *     Browsers fetch it without credentials, so it must stay public.
         */
        get: operations["public_manifest_api_v1_public_manifest_webmanifest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/banner": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Public Banner
         * @description The active banner, or null. Public, since the login page shows it.
         */
        get: operations["public_banner_api_v1_public_banner_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/branding/login-background": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Public Login Background
         * @description The background photo of the sign-in screens, without a session, since
         *     nobody is signed in there. Only the file the general settings name is
         *     served here.
         */
        get: operations["public_login_background_api_v1_public_branding_login_background_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/legal/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Legal Page
         * @description The current imprint or privacy statement, without a session, since
         *     the login page links both.
         */
        get: operations["read_legal_page_api_v1_public_legal__kind__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/recipes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Public Recipes
         * @description The public recipes, newest first or by title, with text search and
         *     the filters that need no personal data.
         */
        get: operations["list_public_recipes_api_v1_public_recipes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/recipes/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Public Recipe Tags
         * @description The tags the public recipes carry, for the tag filter.
         */
        get: operations["list_public_recipe_tags_api_v1_public_recipes_tags_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/recipes/{recipe_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Public Recipe
         * @description One public recipe with what is derived from it, scaled to `servings`.
         *     Anything that is not a public recipe answers 404 like an unknown id.
         */
        get: operations["read_public_recipe_api_v1_public_recipes__recipe_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/recipes/{recipe_id}/images/{image_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Public Recipe Image
         * @description An image of a public recipe (its cover or a step image) in display
         *     size, inline. The original is never served here, and a file that is not
         *     an image of a recipe the visitor may see answers 404.
         */
        get: operations["read_public_recipe_image_api_v1_public_recipes__recipe_id__images__image_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/public/recipes/{recipe_id}/author-avatar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Public Recipe Author Avatar
         * @description The avatar of a public recipe's author in display size, only while
         *     the author shows their name on public recipes (`author_avatar` on the
         *     recipe); 404 otherwise, like an unknown recipe.
         */
        get: operations["read_public_recipe_author_avatar_api_v1_public_recipes__recipe_id__author_avatar_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pat/version": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pat Version */
        get: operations["pat_version_api_v1_pat_version_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pat/users/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pat Me */
        get: operations["pat_me_api_v1_pat_users_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/key/whoami": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Key Whoami */
        get: operations["key_whoami_api_v1_key_whoami_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health
         * @description Liveness: the process answers.
         */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ready
         * @description Readiness: the database and Redis answer.
         */
        get: operations["ready_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AcceptIncomingRecipeRequest */
        AcceptIncomingRecipeRequest: {
            /** Decisions */
            decisions?: components["schemas"]["MappingDecisionRequest"][];
        };
        /** AcceptPeerInvitationRequest */
        AcceptPeerInvitationRequest: {
            /** Invitation Url */
            invitation_url: string;
        };
        /** AcceptReferenceUpdateRequest */
        AcceptReferenceUpdateRequest: {
            /** Kind */
            kind: string;
            /** Key */
            key: string;
            /** Field */
            field: string;
        };
        /**
         * AcceptedRecipeResponse
         * @description The mirror the accepted recipe became or updated.
         */
        AcceptedRecipeResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
        };
        /**
         * AcceptedWaitingResponse
         * @description How many waiting recipes of a peer became mirrors.
         */
        AcceptedWaitingResponse: {
            /** Accepted */
            accepted: number;
        };
        /**
         * AccountDeletionImpact
         * @description What deleting an account touches, for the confirmation dialog.
         *     Backups keep the data until they rotate out.
         */
        AccountDeletionImpact: {
            /** Recipes */
            recipes: {
                [key: string]: number;
            };
            /** Drafts */
            drafts: number;
            /** Ingredients */
            ingredients: number;
            /** Lists Handed Over */
            lists_handed_over: number;
            /** Lists Deleted */
            lists_deleted: number;
            /** In Household */
            in_household: boolean;
            /** Backup Keep Days */
            backup_keep_days: number;
            /**
             * Backups Clear By
             * Format: date
             */
            backups_clear_by: string;
        };
        /** AcknowledgementOverviewResponse */
        AcknowledgementOverviewResponse: {
            /**
             * Notice Id
             * Format: uuid
             */
            notice_id: string;
            /** Acknowledged */
            acknowledged: components["schemas"]["AcknowledgementResponse"][];
            /** Pending */
            pending: components["schemas"]["UserSummaryResponse"][];
        };
        /** AcknowledgementResponse */
        AcknowledgementResponse: {
            user: components["schemas"]["UserSummaryResponse"];
            /**
             * Acknowledged At
             * Format: date-time
             */
            acknowledged_at: string;
        };
        /** AddRecipeToListRequest */
        AddRecipeToListRequest: {
            /**
             * Recipe Id
             * Format: uuid
             */
            recipe_id: string;
            /** Servings */
            servings?: number | null;
            /** Bought Sub Recipe Ids */
            bought_sub_recipe_ids?: string[];
        };
        /** AddedResponse */
        AddedResponse: {
            /** Added */
            added: number;
        };
        /** AdoptVariationRequest */
        AdoptVariationRequest: {
            /** Change Ids */
            change_ids?: string[] | null;
            /** Revision Note */
            revision_note?: string | null;
        };
        /** AdoptVariationResponse */
        AdoptVariationResponse: {
            recipe: components["schemas"]["RecipeEditResponse"];
            variation: components["schemas"]["VariationResponse"];
        };
        /**
         * AgentCallOutcome
         * @enum {string}
         */
        AgentCallOutcome: "ok" | "error" | "refused";
        /** AgentCallResponse */
        AgentCallResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Called At
             * Format: date-time
             */
            called_at: string;
            /** User Id */
            user_id: string | null;
            /** User Name */
            user_name: string | null;
            /** Token Kind */
            token_kind: string;
            /** Token Name */
            token_name: string;
            /** Tool */
            tool: string;
            /** Arguments */
            arguments: {
                [key: string]: unknown;
            };
            /** Outcome */
            outcome: string;
            /** Duration Ms */
            duration_ms: number;
            /** Error */
            error: string | null;
            /** Created Refs */
            created_refs: string[];
        };
        /** AgentSettingsSchema */
        AgentSettingsSchema: {
            /** Enabled */
            enabled: boolean;
            /** Calls Per Minute */
            calls_per_minute: number;
            /** Drafts Per Hour */
            drafts_per_hour: number;
            /** Token Max Lifetime Days */
            token_max_lifetime_days: number;
            /**
             * Oauth Enabled
             * @default true
             */
            oauth_enabled: boolean;
            /** Oauth Redirect Hosts */
            oauth_redirect_hosts?: string[];
        };
        /** AlertResponse */
        AlertResponse: {
            /** Kind */
            kind: string;
            /** Description */
            description: string;
        };
        /**
         * Allergen
         * @description The 14 allergens EU food law requires to be declared.
         * @enum {string}
         */
        Allergen: "gluten" | "crustaceans" | "eggs" | "fish" | "peanuts" | "soybeans" | "milk" | "nuts" | "celery" | "mustard" | "sesame" | "sulphites" | "lupin" | "molluscs";
        /**
         * AmountStyle
         * @description How a user reads small metric amounts in recipes, a display
         *     preference only. Counts read as fractions either way.
         * @enum {string}
         */
        AmountStyle: "decimals" | "fractions";
        /** ApiKeyCreatedResponse */
        ApiKeyCreatedResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Token Prefix */
            token_prefix: string;
            /** Permissions */
            permissions: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
            /** Token */
            token: string;
        };
        /** ApiKeyResponse */
        ApiKeyResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Token Prefix */
            token_prefix: string;
            /** Permissions */
            permissions: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
        };
        /** AuthorizationDecisionRequest */
        AuthorizationDecisionRequest: {
            request: components["schemas"]["AuthorizationRequestSchema"];
            /** Approve */
            approve: boolean;
            /** Permissions */
            permissions?: string[];
        };
        /** AuthorizationDecisionResponse */
        AuthorizationDecisionResponse: {
            /** Redirect To */
            redirect_to: string;
        };
        /** AuthorizationPromptResponse */
        AuthorizationPromptResponse: {
            /** Client Name */
            client_name: string;
            /** Client Uri */
            client_uri: string | null;
            /** Redirect Host */
            redirect_host: string;
            /** Offered */
            offered: string[];
            /** Requested */
            requested: string[];
            /** Error Redirect */
            error_redirect: string | null;
        };
        /**
         * AuthorizationRequestSchema
         * @description The query of the authorization URL, which the consent page forwards
         *     as it received it.
         */
        AuthorizationRequestSchema: {
            /** Client Id */
            client_id: string;
            /** Redirect Uri */
            redirect_uri?: string | null;
            /** Response Type */
            response_type?: string | null;
            /** Code Challenge */
            code_challenge?: string | null;
            /** Code Challenge Method */
            code_challenge_method?: string | null;
            /** State */
            state?: string | null;
            /** Scope */
            scope?: string | null;
            /** Resource */
            resource?: string | null;
        };
        /** BackupFileResponse */
        BackupFileResponse: {
            /** Name */
            name: string;
            /** Size Bytes */
            size_bytes: number;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** BackupReadingResponse */
        BackupReadingResponse: {
            /** Visible */
            visible: boolean;
            /** Keep Days */
            keep_days: number;
            /** Hour Utc */
            hour_utc: number;
            /** Newest */
            newest: string | null;
            /** Files */
            files: components["schemas"]["BackupFileResponse"][];
        };
        /** BackupRetentionResponse */
        BackupRetentionResponse: {
            /** Keep Days */
            keep_days: number;
            /** Gone By */
            gone_by: string;
        };
        /** BackupRunStatusResponse */
        BackupRunStatusResponse: {
            /** Trigger */
            trigger: string;
            /**
             * Started
             * Format: date-time
             */
            started: string;
            /** Finished */
            finished: string | null;
            /** Ok */
            ok: boolean | null;
            /** File */
            file: string | null;
        };
        /** BannerSettingsSchema */
        BannerSettingsSchema: {
            /** Enabled */
            enabled: boolean;
            severity: components["schemas"]["BannerSeverity"];
            /** Messages */
            messages: {
                [key: string]: string;
            };
            /** Starts At */
            starts_at?: string | null;
            /** Ends At */
            ends_at?: string | null;
            /**
             * Dismissible
             * @default true
             */
            dismissible: boolean;
        };
        /**
         * BannerSeverity
         * @enum {string}
         */
        BannerSeverity: "info" | "warning" | "critical";
        /**
         * BasedOnRef
         * @description The recipe a copy was made from: with link, title and owner when the
         *     viewer may see it, as an anonymous placeholder otherwise.
         */
        BasedOnRef: {
            recipe: components["schemas"]["SubRecipeRef"];
            owner: components["schemas"]["PersonRef"] | null;
        };
        /** Body_import_catalogue_api_v1_web_admin_catalogue_import_post */
        Body_import_catalogue_api_v1_web_admin_catalogue_import_post: {
            /**
             * File
             * @description A `cuisine-catalogue` JSON file.
             */
            file: string;
            /**
             * Accept
             * @description The differences to write, each as `<kind>:<source id>:<field>`; every other difference changes nothing.
             */
            accept?: string[];
        };
        /** Body_import_mail_template_api_v1_web_settings_mail_templates__kind__import_post */
        Body_import_mail_template_api_v1_web_settings_mail_templates__kind__import_post: {
            /**
             * Locale
             * @enum {string}
             */
            locale: "en-GB" | "de-AT";
            /** File */
            file: string;
        };
        /** Body_import_recipes_api_v1_web_recipes_import_post */
        Body_import_recipes_api_v1_web_recipes_import_post: {
            /**
             * File
             * @description A `.cui` file or an older recipe archive.
             */
            file: string;
            /**
             * Update
             * @description Source ids of recipes whose earlier import the caller wants updated; every other recipe imported before becomes a new copy.
             */
            update?: string[];
        };
        /** Body_preview_catalogue_import_api_v1_web_admin_catalogue_import_preview_post */
        Body_preview_catalogue_import_api_v1_web_admin_catalogue_import_preview_post: {
            /**
             * File
             * @description A `cuisine-catalogue` JSON file.
             */
            file: string;
        };
        /** Body_preview_import_api_v1_web_recipes_import_preview_post */
        Body_preview_import_api_v1_web_recipes_import_preview_post: {
            /**
             * File
             * @description A `.cui` file or an older recipe archive.
             */
            file: string;
        };
        /** Body_replace_avatar_api_v1_web_users_me_avatar_put */
        Body_replace_avatar_api_v1_web_users_me_avatar_put: {
            /** File */
            file: string;
        };
        /** Body_replace_user_avatar_api_v1_web_users__user_id__avatar_put */
        Body_replace_user_avatar_api_v1_web_users__user_id__avatar_put: {
            /** File */
            file: string;
        };
        /** Body_upload_file_api_v1_web_files_post */
        Body_upload_file_api_v1_web_files_post: {
            /** File */
            file: string;
        };
        /**
         * CatalogueConflictResponse
         * @description Something of the file that is or was not written as it is.
         */
        CatalogueConflictResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "category" | "family" | "unit" | "tag" | "ingredient" | "equipment";
            /** Name */
            name: string;
            /** Detail */
            detail: string;
        };
        /** CatalogueCreatedResponse */
        CatalogueCreatedResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "category" | "family" | "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Name */
            name: string;
            /** Id */
            id: string;
        };
        /**
         * CatalogueFieldDifferenceResponse
         * @description A field whose value here differs from the file's. Field names and
         *     values follow the reference data updates (`names.de-AT`, `allergens`,
         *     `nutrition.kcal`, ...); references are shown by name and conversions as
         *     unit code to grams.
         */
        CatalogueFieldDifferenceResponse: {
            /** Field */
            field: string;
            /** Current */
            current: unknown;
            /** Incoming */
            incoming: unknown;
        };
        /** CatalogueImportResponse */
        CatalogueImportResponse: {
            /** Created */
            created: components["schemas"]["CatalogueCreatedResponse"][];
            /** Updated */
            updated: components["schemas"]["CatalogueUpdatedResponse"][];
            /** Skipped */
            skipped: ("category" | "family" | "unit" | "tag" | "ingredient" | "equipment")[];
            /** Conflicts */
            conflicts: components["schemas"]["CatalogueConflictResponse"][];
        };
        /** CatalogueKindSummaryResponse */
        CatalogueKindSummaryResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "category" | "family" | "unit" | "tag" | "ingredient" | "equipment";
            /** Total */
            total: number;
            /** New */
            new: number;
            /** Matched */
            matched: number;
            /** Different */
            different: number;
            /** Skipped */
            skipped: boolean;
        };
        /** CataloguePreviewEntryResponse */
        CataloguePreviewEntryResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "category" | "family" | "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Name */
            name: string;
            /** Local Id */
            local_id: string | null;
            /** Differences */
            differences: components["schemas"]["CatalogueFieldDifferenceResponse"][];
        };
        /** CataloguePreviewResponse */
        CataloguePreviewResponse: {
            /** Source Instance Id */
            source_instance_id: string | null;
            /** Exported At */
            exported_at: string;
            /** Kinds */
            kinds: components["schemas"]["CatalogueKindSummaryResponse"][];
            /** Entries */
            entries: components["schemas"]["CataloguePreviewEntryResponse"][];
            /** Conflicts */
            conflicts: components["schemas"]["CatalogueConflictResponse"][];
        };
        /**
         * CatalogueSuggestion
         * @description A local entry that probably means the same, found by name or alias;
         *     never taken without a decision.
         */
        CatalogueSuggestion: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** CatalogueUpdatedResponse */
        CatalogueUpdatedResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "category" | "family" | "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Name */
            name: string;
            /** Id */
            id: string;
            /** Fields */
            fields: string[];
        };
        /** CategoryRef */
        CategoryRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Sort Order */
            sort_order: number;
        };
        /** CategoryRequest */
        CategoryRequest: {
            /**
             * Sort Order
             * @default 0
             */
            sort_order: number;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** CategoryResponse */
        CategoryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Seeded */
            seeded: boolean;
            /** Sort Order */
            sort_order: number;
            /** Name */
            name: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** ChangePasswordRequest */
        ChangePasswordRequest: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /** CoEditorsRequest */
        CoEditorsRequest: {
            /** User Ids */
            user_ids?: string[];
        };
        /** ConnectedAppResponse */
        ConnectedAppResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Client Name */
            client_name: string;
            /** Client Uri */
            client_uri: string | null;
            /** Redirect Host */
            redirect_host: string;
            /** Permissions */
            permissions: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
        };
        /** ConsentResponse */
        ConsentResponse: {
            /** Kind */
            kind: string;
            /** Granted */
            granted: boolean;
            /** Granted At */
            granted_at: string | null;
        };
        /**
         * ContentLocale
         * @description The languages recipe and resource text is written in, as BCP 47
         *     tags. The UI languages are the same two.
         * @enum {string}
         */
        ContentLocale: "de-AT" | "en-GB";
        /** ConversionRequest */
        ConversionRequest: {
            /**
             * Unit Id
             * Format: uuid
             */
            unit_id: string;
            /** Grams */
            grams: number;
        };
        /** ConversionResponse */
        ConversionResponse: {
            /**
             * Unit Id
             * Format: uuid
             */
            unit_id: string;
            /** Unit Code */
            unit_code: string;
            /** Unit Name */
            unit_name: string;
            /** Grams */
            grams: number;
        };
        /** CookEventRequest */
        CookEventRequest: {
            /**
             * Recipe Id
             * Format: uuid
             */
            recipe_id: string;
            /** Variation Id */
            variation_id?: string | null;
            /**
             * Cooked On
             * Format: date
             */
            cooked_on: string;
            /** Servings */
            servings: number;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** CookEventResponse */
        CookEventResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Cooked On
             * Format: date
             */
            cooked_on: string;
            /** Servings */
            servings: number;
            /** Note */
            note: string;
            user: components["schemas"]["PersonRef"] | null;
            recipe: components["schemas"]["RecipeRef"] | null;
            variation?: components["schemas"]["VariationRef"] | null;
            /** Is Own */
            is_own: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** CookEventUpdate */
        CookEventUpdate: {
            /**
             * Cooked On
             * Format: date
             */
            cooked_on: string;
            /** Servings */
            servings: number;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /**
         * CookModeLayout
         * @description How cook mode lays out a recipe's steps, a display preference only.
         * @enum {string}
         */
        CookModeLayout: "step" | "flow";
        /** CookOnceRequest */
        CookOnceRequest: {
            /**
             * Recipe Id
             * Format: uuid
             */
            recipe_id: string;
            /** Variation Id */
            variation_id?: string | null;
            /**
             * Cooked On
             * Format: date
             */
            cooked_on: string;
            /** Servings */
            servings: number;
        };
        /** CookOnceResponse */
        CookOnceResponse: {
            event: components["schemas"]["CookEventResponse"];
            /** Created */
            created: boolean;
        };
        /** CreateGroupRequest */
        CreateGroupRequest: {
            /** Name */
            name: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** Permissions */
            permissions?: string[];
            /** Member Ids */
            member_ids?: string[];
        };
        /** CreateUserRequest */
        CreateUserRequest: {
            /** Full Name */
            full_name: string;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
            /** Permissions */
            permissions?: string[];
            /** Group Ids */
            group_ids?: string[];
            language?: components["schemas"]["Language"] | null;
            /**
             * Is Active
             * @default true
             */
            is_active: boolean;
            /** Nickname */
            nickname?: string | null;
            /**
             * Show Nickname
             * @default false
             */
            show_nickname: boolean;
        };
        /**
         * CreatedPeerInvitationResponse
         * @description Answers creating an invitation: the only time the link is shown.
         */
        CreatedPeerInvitationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Link */
            link: string;
        };
        /** CurrentSessionResponse */
        CurrentSessionResponse: {
            /** Expires At */
            expires_at: string | null;
            /**
             * Server Time
             * Format: date-time
             */
            server_time: string;
        };
        /** CurrentUserResponse */
        CurrentUserResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Full Name */
            full_name: string;
            /** Nickname */
            nickname: string | null;
            /** Show Nickname */
            show_nickname: boolean;
            /** Display Name */
            display_name: string;
            /** Email */
            email: string;
            /** Is Active */
            is_active: boolean;
            /** Is Systemuser */
            is_systemuser: boolean;
            /** Permissions */
            permissions: string[];
            /** Effective Permissions */
            effective_permissions: string[];
            /** Group Ids */
            group_ids: string[];
            language: components["schemas"]["Language"];
            /** Totp Enabled */
            totp_enabled: boolean;
            /** Totp Mandatory */
            totp_mandatory: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Last Logged In */
            last_logged_in: string | null;
            /** Avatar Id */
            avatar_id?: string | null;
            theme_preset: components["schemas"]["ThemePreset"];
            theme_surface: components["schemas"]["ThemeSurface"];
            theme_primary: components["schemas"]["ThemePrimary"];
            /** Theme Dark Mode */
            theme_dark_mode: boolean;
            amount_style: components["schemas"]["AmountStyle"];
            /** Share Restrictions With Hosts */
            share_restrictions_with_hosts: boolean;
            /** Default Recipe Visibility */
            default_recipe_visibility: string | null;
            /** Show Name On Public Recipes */
            show_name_on_public_recipes: boolean;
            /** Show Name On Paired Instances */
            show_name_on_paired_instances: boolean;
            /** Recipe Show Tips */
            recipe_show_tips: boolean;
            /** Recipe Show Notes */
            recipe_show_notes: boolean;
            /** Recipe Show Cooked */
            recipe_show_cooked: boolean;
            /** Recipe Show Rating */
            recipe_show_rating: boolean;
            /** Recipe Highlight Mentions */
            recipe_highlight_mentions: boolean;
            /** Keep Screen On */
            keep_screen_on: boolean;
            cook_mode_layout: components["schemas"]["CookModeLayout"];
            /**
             * Privacy Acknowledgement Pending
             * @default false
             */
            privacy_acknowledgement_pending: boolean;
            /** Privacy Version */
            privacy_version?: number | null;
            /** Privacy Acknowledged Version */
            privacy_acknowledged_version?: number | null;
            privacy_mode?: components["schemas"]["PrivacyModeResponse"] | null;
            /** Consent Health Data At */
            consent_health_data_at?: string | null;
            /** Consent Ai Agents At */
            consent_ai_agents_at?: string | null;
        };
        /** DatabaseReadingResponse */
        DatabaseReadingResponse: {
            /** Dialect */
            dialect: string;
            /** Size Bytes */
            size_bytes: number | null;
            /** Largest Tables */
            largest_tables: components["schemas"]["TableSizeResponse"][];
        };
        /**
         * DateFormat
         * @enum {string}
         */
        DateFormat: "dd.mm.yyyy" | "dd/mm/yyyy" | "yyyy-mm-dd" | "mm/dd/yyyy";
        /**
         * Diet
         * @description The diets a user may follow. Which ingredients break them is decided
         *     by the ingredients' diet markers (services/diet_rules.py).
         * @enum {string}
         */
        Diet: "vegetarian" | "vegan" | "pescetarian" | "halal" | "no_pork" | "no_beef" | "no_alcohol";
        /**
         * DietMarker
         * @description What an ingredient is or contains, as far as diets care.
         * @enum {string}
         */
        DietMarker: "meat" | "poultry" | "pork" | "beef" | "fish" | "seafood" | "gelatin" | "dairy" | "eggs" | "honey" | "alcohol";
        /**
         * Difficulty
         * @enum {string}
         */
        Difficulty: "easy" | "medium" | "hard";
        /**
         * DirectoryUserResponse
         * @description An entry of the people directory, with the avatar so pickers can show
         *     the face next to the name. Every signed-in user may read every avatar.
         */
        DirectoryUserResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
            /** Avatar Id */
            avatar_id: string | null;
        };
        /** DuplicateCandidate */
        DuplicateCandidate: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Matched */
            matched: string;
            /** Exact */
            exact: boolean;
        };
        /**
         * EarlierImportResponse
         * @description A recipe of the importer's that an earlier import of the same source
         *     recipe created.
         */
        EarlierImportResponse: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "published";
        };
        /** EquipmentDeletionImpact */
        EquipmentDeletionImpact: {
            /** Seeded */
            seeded: boolean;
            /** Recipe Count */
            recipe_count: number;
            /** Recipes */
            recipes: components["schemas"]["RecipeRef"][];
            /** Can Merge */
            can_merge: boolean;
        };
        /** EquipmentDuplicate */
        EquipmentDuplicate: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Matched */
            matched: string;
            /** Exact */
            exact: boolean;
        };
        /**
         * EquipmentKind
         * @enum {string}
         */
        EquipmentKind: "cookware" | "bakeware" | "appliance" | "utensil";
        /**
         * EquipmentNeed
         * @description One line of "You'll need": the highest count a single step names,
         *     and the sub-recipe whose steps need it (null for the recipe's own).
         */
        EquipmentNeed: {
            equipment: components["schemas"]["EquipmentRef"];
            /** Count */
            count: number | null;
            sub_recipe: components["schemas"]["SubRecipeRef"] | null;
            /** Missing */
            missing: boolean | null;
        };
        /** EquipmentRef */
        EquipmentRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Kind */
            kind: string;
            /** Icon */
            icon: string | null;
        };
        /** EquipmentRequest */
        EquipmentRequest: {
            kind: components["schemas"]["EquipmentKind"];
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
            /** Aliases */
            aliases?: {
                [key: string]: string[];
            };
            /** Icon */
            icon?: string | null;
            /**
             * Basic
             * @default false
             */
            basic: boolean;
        };
        /** EquipmentResponse */
        EquipmentResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Locale */
            locale: string;
            /** Available Locales */
            available_locales: string[];
            /** Kind */
            kind: string;
            /** Icon */
            icon: string | null;
            /** Basic */
            basic: boolean;
            /** Status */
            status: string;
            /** Seeded */
            seeded: boolean;
            /** Aliases */
            aliases: {
                [key: string]: string[];
            };
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
        };
        /**
         * EquipmentStatus
         * @enum {string}
         */
        EquipmentStatus: "draft" | "active";
        /**
         * ExtendedNutrientAmount
         * @description An extended nutrient summed over the recipe (`total` for the
         *     servings asked for). `complete` is false when an amount could not be
         *     weighed or a counted ingredient does not state this nutrient.
         */
        ExtendedNutrientAmount: {
            /** Key */
            key: string;
            /** Unit */
            unit: string;
            /** Total */
            total: number;
            /** Per Serving */
            per_serving: number;
            /** Complete */
            complete: boolean;
        };
        /**
         * ExtendedNutrientResponse
         * @description One entry of the extended nutrient catalogue. The amount is per
         *     100 g in `unit` (mg, ug or g); `label_key` names the label in the
         *     frontend's locale files.
         */
        ExtendedNutrientResponse: {
            /** Key */
            key: string;
            /** Unit */
            unit: string;
            /** Label Key */
            label_key: string;
            /** Usda Nutrient Id */
            usda_nutrient_id: number;
        };
        /** FamilyRef */
        FamilyRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** FamilyRequest */
        FamilyRequest: {
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** FamilyResponse */
        FamilyResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Seeded */
            seeded: boolean;
            /** Name */
            name: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** FavouriteRequest */
        FavouriteRequest: {
            /** Favourite */
            favourite: boolean;
        };
        /** FeatureSettingsSchema */
        FeatureSettingsSchema: {
            /** Agents */
            agents: boolean;
            /** Webhooks */
            webhooks: boolean;
            /** Households */
            households: boolean;
            /** Dinner Guests */
            dinner_guests: boolean;
            /** Usda */
            usda: boolean;
            /** Peering */
            peering: boolean;
        };
        /** FileKindCountResponse */
        FileKindCountResponse: {
            /** Kind */
            kind: string;
            /** Count */
            count: number;
            /** Bytes */
            bytes: number;
        };
        /** FileReadingResponse */
        FileReadingResponse: {
            /** Count */
            count: number;
            /** Original Bytes */
            original_bytes: number;
            /** Thumbnail Bytes */
            thumbnail_bytes: number;
            /** By Kind */
            by_kind: components["schemas"]["FileKindCountResponse"][];
        };
        /**
         * FoodFactResponse
         * @description The food fact of the day, about one base ingredient.
         */
        FoodFactResponse: {
            /** Key */
            key: string;
            /** Text */
            text: string;
            /** Locale */
            locale: string;
            /**
             * Ingredient Id
             * Format: uuid
             */
            ingredient_id: string;
            /** Ingredient Name */
            ingredient_name: string;
            /** Source Title */
            source_title: string;
            /** Source Url */
            source_url: string;
        };
        /** FoodMatchResponse */
        FoodMatchResponse: {
            /** Fdc Id */
            fdc_id: number;
            /** Description */
            description: string;
            /** Data Type */
            data_type: string;
            /** Brand */
            brand: string | null;
            nutrition: components["schemas"]["NutritionSchema"];
            /** Extended Nutrition */
            extended_nutrition: {
                [key: string]: number;
            };
        };
        /**
         * FoodRestrictionRequest
         * @description Exactly one of allergen, ingredient_id, ingredient_name and diet; a
         *     diet goes with kind "diet". An unknown ingredient_name creates a draft
         *     ingredient of that name.
         */
        FoodRestrictionRequest: {
            kind: components["schemas"]["RestrictionKind"];
            allergen?: components["schemas"]["Allergen"] | null;
            /** Ingredient Id */
            ingredient_id?: string | null;
            /** Ingredient Name */
            ingredient_name?: string | null;
            diet?: components["schemas"]["Diet"] | null;
            /** Family Id */
            family_id?: string | null;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** FoodRestrictionResponse */
        FoodRestrictionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Allergen */
            allergen: string | null;
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Ingredient Name */
            ingredient_name: string | null;
            /** Diet */
            diet: string | null;
            /** Family Id */
            family_id: string | null;
            /** Family Name */
            family_name: string | null;
            /** Note */
            note: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** GeneralSettingsSchema */
        GeneralSettingsSchema: {
            /** Instance Name */
            instance_name: string;
            default_language: components["schemas"]["Language"];
            /**
             * Accent Color
             * @default
             */
            accent_color: string;
            /** Login Background File Id */
            login_background_file_id?: string | null;
            /**
             * Login Steam
             * @default true
             */
            login_steam: boolean;
            /** @default metric */
            unit_system: components["schemas"]["UnitSystem"];
            /** @default dd.mm.yyyy */
            date_format: components["schemas"]["DateFormat"];
            /** @default 24h */
            time_format: components["schemas"]["TimeFormat"];
            /** @default monday */
            first_day_of_week: components["schemas"]["Weekday"];
        };
        /** GroupResponse */
        GroupResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            /** Permissions */
            permissions: string[];
            /** Member Ids */
            member_ids: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /**
         * GroupSummaryResponse
         * @description What every signed-in user may see of a group: enough to share a
         *     recipe with it.
         */
        GroupSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HandedOverRecipe
         * @description An own recipe or draft that another user's recipe uses as a
         *     sub-recipe; it passes to that recipe's owner instead of being deleted.
         */
        HandedOverRecipe: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** New Owner Name */
            new_owner_name: string;
        };
        /** HealthResponse */
        HealthResponse: {
            /** Status */
            status: string;
            /** Checks */
            checks?: {
                [key: string]: string;
            };
        };
        /** HomeResponse */
        HomeResponse: {
            food_fact: components["schemas"]["FoodFactResponse"] | null;
            /** On This Day */
            on_this_day: components["schemas"]["CookEventResponse"][];
            /** Recently Cooked */
            recently_cooked: components["schemas"]["CookEventResponse"][];
            /** Favourites */
            favourites: components["schemas"]["RecipeSummaryResponse"][];
            /** Newest */
            newest: components["schemas"]["RecipeSummaryResponse"][];
            /** In Season */
            in_season: components["schemas"]["RecipeSummaryResponse"][];
        };
        /** HostStatusResponse */
        HostStatusResponse: {
            /** App Version */
            app_version: string;
            /**
             * Instance Id
             * Format: uuid
             */
            instance_id: string;
            /** Hostname */
            hostname: string;
            /** Platform */
            platform: string;
            /** Python Version */
            python_version: string;
            /**
             * Boot Time
             * Format: date-time
             */
            boot_time: string;
            /**
             * Process Start Time
             * Format: date-time
             */
            process_start_time: string;
            /** Cpu Count */
            cpu_count: number;
            /** Cpu Percent */
            cpu_percent: number;
            /** Load Average */
            load_average: number[] | null;
            /** Memory Total Bytes */
            memory_total_bytes: number;
            /** Memory Used Bytes */
            memory_used_bytes: number;
            /** Memory Percent */
            memory_percent: number;
            /** Disk Path */
            disk_path: string;
            /** Disk Total Bytes */
            disk_total_bytes: number;
            /** Disk Used Bytes */
            disk_used_bytes: number;
            /** Disk Percent */
            disk_percent: number;
            /** Services */
            services: components["schemas"]["ServiceReadingResponse"][];
        };
        /**
         * HouseholdMembershipResponse
         * @description What administrators see: who belongs to which household.
         */
        HouseholdMembershipResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Members */
            members: components["schemas"]["PersonRef"][];
        };
        /** HouseholdRef */
        HouseholdRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** HouseholdRequest */
        HouseholdRequest: {
            /** Name */
            name: string;
        };
        /** HouseholdResponse */
        HouseholdResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Members */
            members: components["schemas"]["PersonRef"][];
            /** Invitations */
            invitations: components["schemas"]["SentInvitationResponse"][];
            /** Shopping List Id */
            shopping_list_id: string | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /**
         * ImportConflictResponse
         * @description Something of the archive that could not be placed as it was.
         */
        ImportConflictResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment" | "sub_recipe" | "image" | "title" | "variation" | "status";
            /** Name */
            name: string;
            /** Detail */
            detail: string;
            /** Recipe */
            recipe: string | null;
        };
        /** ImportPreviewRecipeResponse */
        ImportPreviewRecipeResponse: {
            /** Source Id */
            source_id: string;
            /** Title */
            title: string;
            earlier: components["schemas"]["EarlierImportResponse"] | null;
        };
        /** ImportedRecipeResponse */
        ImportedRecipeResponse: {
            /** Source Id */
            source_id: string;
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Updated */
            updated: boolean;
        };
        /** IncomingRecipeResponse */
        IncomingRecipeResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            peer: components["schemas"]["PeerRef"];
            /**
             * Source Id
             * Format: uuid
             */
            source_id: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Author Name */
            author_name: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "rejected";
            /**
             * Kind
             * @enum {string}
             */
            kind: "new" | "update";
            /** Mirror Id */
            mirror_id: string | null;
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            /** Decided At */
            decided_at: string | null;
            /** Entries */
            entries: components["schemas"]["NeededEntryResponse"][];
            /** Sub Recipes */
            sub_recipes: components["schemas"]["IncomingSubRecipe"][];
        };
        /** IncomingSubRecipe */
        IncomingSubRecipe: {
            /** Source Id */
            source_id: string;
            /** Title */
            title: string | null;
            /** Mirrored */
            mirrored: boolean;
            /** Waiting */
            waiting: boolean;
        };
        /**
         * IngredientAmount
         * @description A catalogue ingredient (`ingredient_id`) or a sub-recipe
         *     (`sub_recipe`).
         */
        IngredientAmount: {
            /** Ingredient Id */
            ingredient_id: string | null;
            sub_recipe?: components["schemas"]["SubRecipeRef"] | null;
            /** Name */
            name: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            /** Note */
            note: string;
            /** Category Id */
            category_id?: string | null;
            /** Line Id */
            line_id?: string | null;
        };
        /** IngredientDeletionImpact */
        IngredientDeletionImpact: {
            /** Seeded */
            seeded: boolean;
            /** Recipe Count */
            recipe_count: number;
            /** Recipes */
            recipes: components["schemas"]["RecipeRef"][];
            /** Can Merge */
            can_merge: boolean;
        };
        /** IngredientDetailResponse */
        IngredientDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Plural Name */
            plural_name: string;
            /** Locale */
            locale: string;
            /** Original Locale */
            original_locale: string;
            /** Available Locales */
            available_locales: string[];
            category: components["schemas"]["CategoryRef"] | null;
            family: components["schemas"]["FamilyRef"] | null;
            /** Aliases */
            aliases: {
                [key: string]: string[];
            };
            nutrition: components["schemas"]["NutritionSchema"];
            /** Extended Nutrition */
            extended_nutrition: {
                [key: string]: number;
            };
            /** Season Months */
            season_months: number[];
            /** Density G Per Ml */
            density_g_per_ml: number | null;
            /** Conversions */
            conversions: components["schemas"]["ConversionResponse"][];
            /** Allergens */
            allergens: string[];
            /** Diet Markers */
            diet_markers: string[];
            /** Status */
            status: string;
            /** Nutrition Source */
            nutrition_source: string;
            /** Usda Fdc Id */
            usda_fdc_id: number | null;
            owner: components["schemas"]["PersonRef"] | null;
            /** Can Edit */
            can_edit: boolean;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /** Matched Alias */
            matched_alias?: string | null;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["IngredientTextSchema"];
            };
            /** Recipe Count */
            recipe_count: number;
        };
        /** IngredientListItem */
        IngredientListItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Plural Name */
            plural_name: string;
            /** Locale */
            locale: string;
            /** Original Locale */
            original_locale: string;
            /** Available Locales */
            available_locales: string[];
            category: components["schemas"]["CategoryRef"] | null;
            family: components["schemas"]["FamilyRef"] | null;
            /** Aliases */
            aliases: {
                [key: string]: string[];
            };
            nutrition: components["schemas"]["NutritionSchema"];
            /** Extended Nutrition */
            extended_nutrition: {
                [key: string]: number;
            };
            /** Season Months */
            season_months: number[];
            /** Density G Per Ml */
            density_g_per_ml: number | null;
            /** Conversions */
            conversions: components["schemas"]["ConversionResponse"][];
            /** Allergens */
            allergens: string[];
            /** Diet Markers */
            diet_markers: string[];
            /** Status */
            status: string;
            /** Nutrition Source */
            nutrition_source: string;
            /** Usda Fdc Id */
            usda_fdc_id: number | null;
            owner: components["schemas"]["PersonRef"] | null;
            /** Can Edit */
            can_edit: boolean;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /** Matched Alias */
            matched_alias?: string | null;
            /** Usage Count */
            usage_count: number;
        };
        /** IngredientRequest */
        IngredientRequest: {
            original_locale: components["schemas"]["ContentLocale"];
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["IngredientTextSchema"];
            };
            /** Category Id */
            category_id?: string | null;
            /** Family Id */
            family_id?: string | null;
            /** Aliases */
            aliases?: {
                [key: string]: string[];
            };
            nutrition?: components["schemas"]["NutritionRequest"];
            /** Extended Nutrition */
            extended_nutrition?: {
                [key: string]: number | null;
            };
            /** Season Months */
            season_months?: number[];
            /** Density G Per Ml */
            density_g_per_ml?: number | null;
            /** Conversions */
            conversions?: components["schemas"]["ConversionRequest"][];
            /** Allergens */
            allergens?: components["schemas"]["Allergen"][];
            /** Diet Markers */
            diet_markers?: components["schemas"]["DietMarker"][];
            /** @default manual */
            nutrition_source: components["schemas"]["NutritionSource"];
            /** Usda Fdc Id */
            usda_fdc_id?: number | null;
        };
        /**
         * IngredientStatus
         * @enum {string}
         */
        IngredientStatus: "draft" | "active" | "archived";
        /** IngredientTextSchema */
        IngredientTextSchema: {
            /** Name */
            name: string;
            /**
             * Plural Name
             * @default
             */
            plural_name: string;
        };
        /** IntegrationSettingsRequest */
        IntegrationSettingsRequest: {
            /** Usda Enabled */
            usda_enabled: boolean;
            /** Usda Api Key */
            usda_api_key?: string | null;
        };
        /** IntegrationSettingsResponse */
        IntegrationSettingsResponse: {
            /** Usda Enabled */
            usda_enabled: boolean;
            /** Usda Api Key Set */
            usda_api_key_set: boolean;
            /** Usda Uses Demo Key */
            usda_uses_demo_key: boolean;
        };
        /** InviteRequest */
        InviteRequest: {
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** KitchenRequest */
        KitchenRequest: {
            /** Equipment Ids */
            equipment_ids: string[];
        };
        /**
         * KitchenResponse
         * @description The viewer's kitchen. Before set-up `set_up` is false, the list is
         *     empty and no recipe is flagged.
         */
        KitchenResponse: {
            /** Set Up */
            set_up: boolean;
            /** Household */
            household: boolean;
            /** Equipment */
            equipment: components["schemas"]["EquipmentRef"][];
            /** Changed */
            changed: string | null;
        };
        /** KitchenSetupRequest */
        KitchenSetupRequest: {
            /** Equipment Ids */
            equipment_ids?: string[] | null;
        };
        /**
         * Language
         * @enum {string}
         */
        Language: "deAT" | "enGB";
        /** LegalDraftResponse */
        LegalDraftResponse: {
            /** Locale */
            locale: string;
            /** Body */
            body: string;
        };
        /**
         * LegalKind
         * @enum {string}
         */
        LegalKind: "imprint" | "privacy";
        /** LegalPageResponse */
        LegalPageResponse: {
            /** Kind */
            kind: string;
            /** Version */
            version: number;
            /** Locale */
            locale: string;
            /** Body */
            body: string;
            /**
             * Published At
             * Format: date-time
             */
            published_at: string;
        };
        /** LegalPublishRequest */
        LegalPublishRequest: {
            /** Texts */
            texts: {
                [key: string]: string;
            };
        };
        /** LegalVersionResponse */
        LegalVersionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Version */
            version: number;
            /** Texts */
            texts: {
                [key: string]: string;
            };
            /**
             * Published At
             * Format: date-time
             */
            published_at: string;
            /** Privacy Mode */
            privacy_mode: string | null;
            /** Default Visibility */
            default_visibility: string | null;
            /** Allow Public Recipes */
            allow_public_recipes?: boolean | null;
            /** Peering Enabled */
            peering_enabled?: boolean | null;
        };
        /**
         * LineMarkerView
         * @description A line of a step in the applied recipe that the variation swapped or
         *     added; `index` counts from 0 within the step's `ingredients`.
         */
        LineMarkerView: {
            /** Index */
            index: number;
            /** Kind */
            kind: string;
            /** Change Id */
            change_id: string;
            /** Swapped From Ingredient Id */
            swapped_from_ingredient_id: string | null;
            /** Swapped From Name */
            swapped_from_name: string | null;
        };
        /** LogEntryResponse */
        LogEntryResponse: {
            /**
             * Time
             * Format: date-time
             */
            time: string;
            /** Level */
            level: string;
            /** Logger */
            logger: string;
            /** Message */
            message: string;
        };
        /**
         * LoginResponse
         * @description What the login step leads to. `session`: signed in, the cookie is
         *     set. `totp_required`: send the code with `partial_token`.
         *     `totp_setup_required`: enrol with `setup_token` as a bearer token.
         */
        LoginResponse: {
            /**
             * Status
             * @enum {string}
             */
            status: "session" | "totp_required" | "totp_setup_required";
            /** Partial Token */
            partial_token?: string | null;
            /** Setup Token */
            setup_token?: string | null;
            /**
             * Trusted Device Days
             * @default 0
             */
            trusted_device_days: number;
        };
        /** MailSettingsRequest */
        MailSettingsRequest: {
            /** Enabled */
            enabled: boolean;
            /** Host */
            host: string;
            /** Port */
            port: number;
            /**
             * Security
             * @enum {string}
             */
            security: "starttls" | "tls" | "none";
            /** Username */
            username: string;
            /** Password */
            password?: string | null;
            /** Sender */
            sender: string;
            /**
             * Sender Name
             * @default
             */
            sender_name: string;
            /**
             * Reply To
             * @default
             */
            reply_to: string;
            /**
             * Verify Certificate
             * @default true
             */
            verify_certificate: boolean;
            /**
             * Send Limit Per Hour
             * @default 60
             */
            send_limit_per_hour: number;
            /** Alert Recipients */
            alert_recipients?: string[];
        };
        /** MailSettingsResponse */
        MailSettingsResponse: {
            /** Enabled */
            enabled: boolean;
            /** Host */
            host: string;
            /** Port */
            port: number;
            /** Security */
            security: string;
            /** Username */
            username: string;
            /** Password Set */
            password_set: boolean;
            /** Sender */
            sender: string;
            /** Sender Name */
            sender_name: string;
            /** Reply To */
            reply_to: string;
            /** Verify Certificate */
            verify_certificate: boolean;
            /** Send Limit Per Hour */
            send_limit_per_hour: number;
            /** Alert Recipients */
            alert_recipients: string[];
        };
        /**
         * MailTemplateKind
         * @enum {string}
         */
        MailTemplateKind: "test_mail" | "operational_alert" | "user_created";
        /** MailTemplateKindResponse */
        MailTemplateKindResponse: {
            /** Kind */
            kind: string;
            /** Variables */
            variables: string[];
            /** Sample Context */
            sample_context: {
                [key: string]: unknown;
            };
            /** Templates */
            templates: components["schemas"]["MailTemplateLocaleResponse"][];
        };
        /** MailTemplateLocaleResponse */
        MailTemplateLocaleResponse: {
            /** Locale */
            locale: string;
            /** Subject */
            subject: string;
            /** Body */
            body: string;
            /** Customized */
            customized: boolean;
        };
        /** MailTemplatePreviewResponse */
        MailTemplatePreviewResponse: {
            /** Subject */
            subject: string;
            /** Html */
            html: string;
        };
        /** MailTemplateTextSchema */
        MailTemplateTextSchema: {
            /**
             * Subject
             * @default
             */
            subject: string;
            /**
             * Body
             * @default
             */
            body: string;
        };
        /** MaintenanceRequest */
        MaintenanceRequest: {
            /** Enabled */
            enabled: boolean;
            /** Messages */
            messages?: {
                [key: string]: string;
            };
        };
        /** MaintenanceResponse */
        MaintenanceResponse: {
            /** Enabled */
            enabled: boolean;
            /** Messages */
            messages: {
                [key: string]: string;
            };
            /** Since */
            since: string | null;
        };
        /** MappingCorrectionRequest */
        MappingCorrectionRequest: {
            /**
             * Action
             * @enum {string}
             */
            action: "map" | "create" | "plain" | "none";
            /** Target Id */
            target_id?: string | null;
            /** Category Id */
            category_id?: string | null;
        };
        /** MappingDecisionRequest */
        MappingDecisionRequest: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "map" | "create" | "plain" | "none";
            /** Target Id */
            target_id?: string | null;
            /** Category Id */
            category_id?: string | null;
        };
        /** MealPlanEntryResponse */
        MealPlanEntryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Plan Date
             * Format: date
             */
            plan_date: string;
            /** Slot */
            slot: string;
            /** Servings */
            servings: number;
            /** Title */
            title: string;
            recipe: components["schemas"]["RecipeRef"] | null;
            scope: components["schemas"]["MealPlanScope"];
        };
        /** MealPlanRequest */
        MealPlanRequest: {
            /**
             * Plan Date
             * Format: date
             */
            plan_date: string;
            slot: components["schemas"]["MealSlot"];
            /** Recipe Id */
            recipe_id?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Servings
             * @default 2
             */
            servings: number;
            scope?: components["schemas"]["MealPlanScope"] | null;
        };
        /**
         * MealPlanScope
         * @description Which plan a request means: the household's, which every member
         *     shares, or the caller's personal one, which only they see.
         * @enum {string}
         */
        MealPlanScope: "household" | "personal";
        /** MealPlanSuggestionResponse */
        MealPlanSuggestionResponse: {
            recipe: components["schemas"]["RecipeSummaryResponse"];
            reason: components["schemas"]["SuggestionReason"];
        };
        /** MealPlanToListRequest */
        MealPlanToListRequest: {
            /**
             * Date From
             * Format: date
             */
            date_from: string;
            /**
             * Date To
             * Format: date
             */
            date_to: string;
            /**
             * List Id
             * Format: uuid
             */
            list_id: string;
            /** Bought Sub Recipe Ids */
            bought_sub_recipe_ids?: string[];
            scope?: components["schemas"]["MealPlanScope"] | null;
        };
        /**
         * MealSlot
         * @enum {string}
         */
        MealSlot: "breakfast" | "lunch" | "dinner" | "snack";
        /** MergeRequest */
        MergeRequest: {
            /**
             * Into Id
             * Format: uuid
             */
            into_id: string;
        };
        /** MirrorPlainEquipment */
        MirrorPlainEquipment: {
            /** Step */
            step: number;
            /** Name */
            name: string;
            /** Count */
            count: number | null;
            /** Note */
            note: string;
        };
        /**
         * MirrorPlainLine
         * @description An ingredient line of a mirror kept as text, with the source's
         *     allergens and diet markers. `step` is the index of its step (from 0) and
         *     `position` its place among that step's ingredient lines as the source
         *     has them.
         */
        MirrorPlainLine: {
            /** Step */
            step: number;
            /** Position */
            position: number;
            /** Name */
            name: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            /** Note */
            note: string;
            /** Allergens */
            allergens: string[];
            /** Diet Markers */
            diet_markers: string[];
        };
        /**
         * MirrorSourceRef
         * @description Where a mirror comes from, for cards: "by <author> · <instance>".
         */
        MirrorSourceRef: {
            /** Instance Name */
            instance_name: string;
            /** Author Name */
            author_name: string | null;
            /** Author Avatar Id */
            author_avatar_id?: string | null;
        };
        /**
         * MirrorUnlinkedSubRecipe
         * @description A sub-recipe line whose sub-recipe is not mirrored here (not shared
         *     with this instance, or not accepted yet); `title` only when the source
         *     shares that sub-recipe with this instance too.
         */
        MirrorUnlinkedSubRecipe: {
            /** Step */
            step: number;
            /** Position */
            position: number;
            /** Title */
            title: string | null;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
        };
        /**
         * MirrorView
         * @description A mirror of a recipe a paired instance shares with this one. It is
         *     read only; `source_url` opens it at its source.
         */
        MirrorView: {
            peer: components["schemas"]["PeerRef"];
            /** Instance Name */
            instance_name: string;
            /** Author Name */
            author_name: string | null;
            /** Author Avatar Id */
            author_avatar_id?: string | null;
            /** Source Url */
            source_url: string;
            /** Source Revision */
            source_revision: string;
            /**
             * Accepted At
             * Format: date-time
             */
            accepted_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Plain Lines */
            plain_lines: components["schemas"]["MirrorPlainLine"][];
            /** Plain Equipment */
            plain_equipment: components["schemas"]["MirrorPlainEquipment"][];
            /** Unlinked Sub Recipes */
            unlinked_sub_recipes: components["schemas"]["MirrorUnlinkedSubRecipe"][];
        };
        /** MyHouseholdResponse */
        MyHouseholdResponse: {
            household: components["schemas"]["HouseholdResponse"] | null;
        };
        /** NameTextSchema */
        NameTextSchema: {
            /** Name */
            name: string;
        };
        /**
         * NeededEntryResponse
         * @description A catalogue entry of the peer without a mapping here. Allowed
         *     decisions: units `map` or `none`; tags `map`, `create` or `none`;
         *     ingredients and equipment `map`, `create` or `plain`.
         */
        NeededEntryResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Name */
            name: string;
            /** Names */
            names: {
                [key: string]: string;
            };
            suggestion: components["schemas"]["CatalogueSuggestion"] | null;
            category_suggestion: components["schemas"]["CatalogueSuggestion"] | null;
            /** Allergens */
            allergens: string[];
            /** Diet Markers */
            diet_markers: string[];
        };
        /** NoteRequest */
        NoteRequest: {
            /** Text */
            text: string;
        };
        /** NoteResponse */
        NoteResponse: {
            /** Text */
            text: string | null;
            /** Changed */
            changed: string | null;
        };
        /** NoteTextSchema */
        NoteTextSchema: {
            /** Note */
            note: string;
        };
        /** NoticeAdminResponse */
        NoticeAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Texts */
            texts: {
                [key: string]: components["schemas"]["NoticeTextResponse"];
            };
            /** Active */
            active: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /** Acknowledged */
            acknowledged: number;
            /** Audience */
            audience: number;
        };
        /** NoticeRequest */
        NoticeRequest: {
            /** Texts */
            texts: {
                [key: string]: components["schemas"]["NoticeTextSchema"];
            };
            /**
             * Active
             * @default true
             */
            active: boolean;
        };
        /**
         * NoticeResponse
         * @description A pending notice for the signed-in user, in their language.
         */
        NoticeResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Locale */
            locale: string;
            /** Title */
            title: string;
            /** Body */
            body: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** NoticeTextResponse */
        NoticeTextResponse: {
            /** Title */
            title: string;
            /** Body */
            body: string;
        };
        /** NoticeTextSchema */
        NoticeTextSchema: {
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Body
             * @default
             */
            body: string;
        };
        /** NotificationSettingsSchema */
        NotificationSettingsSchema: {
            /** Webhooks Enabled */
            webhooks_enabled: boolean;
            /** Allow Private Webhook Targets */
            allow_private_webhook_targets: boolean;
        };
        /** NutritionRequest */
        NutritionRequest: {
            /** Kcal */
            kcal?: number | null;
            /** Protein */
            protein?: number | null;
            /** Fat */
            fat?: number | null;
            /** Saturated Fat */
            saturated_fat?: number | null;
            /** Carbohydrates */
            carbohydrates?: number | null;
            /** Sugar */
            sugar?: number | null;
            /** Fibre */
            fibre?: number | null;
            /** Salt */
            salt?: number | null;
        };
        /**
         * NutritionSchema
         * @description Energy in kcal, everything else in grams. Null means unknown.
         */
        NutritionSchema: {
            /** Kcal */
            kcal?: number | null;
            /** Protein */
            protein?: number | null;
            /** Fat */
            fat?: number | null;
            /** Saturated Fat */
            saturated_fat?: number | null;
            /** Carbohydrates */
            carbohydrates?: number | null;
            /** Sugar */
            sugar?: number | null;
            /** Fibre */
            fibre?: number | null;
            /** Salt */
            salt?: number | null;
        };
        /**
         * NutritionSource
         * @enum {string}
         */
        NutritionSource: "manual" | "usda";
        /** NutritionSourcesResponse */
        NutritionSourcesResponse: {
            /** Credit */
            credit: {
                [key: string]: string;
            };
            /** Citation */
            citation: string;
            /** License */
            license: string;
        };
        /** NutritionView */
        NutritionView: {
            total: components["schemas"]["NutritionSchema"];
            per_serving: components["schemas"]["NutritionSchema"];
            /** Complete */
            complete: boolean;
            /** Missing Ingredient Ids */
            missing_ingredient_ids: string[];
            /** Extended */
            extended: components["schemas"]["ExtendedNutrientAmount"][];
        };
        /**
         * OwnInstanceResponse
         * @description This instance as its peers see it.
         */
        OwnInstanceResponse: {
            /**
             * Instance Id
             * Format: uuid
             */
            instance_id: string;
            /** Name */
            name: string;
            /** Base Url */
            base_url: string;
            /** App Version */
            app_version: string;
            /** Protocol Versions */
            protocol_versions: number[];
            /** Formats */
            formats: {
                [key: string]: number[];
            };
            /** Capabilities */
            capabilities: string[];
        };
        /** OwnRating */
        OwnRating: {
            /** Stars */
            stars: number;
            /** Comment */
            comment: string;
        };
        /** Page[AgentCallResponse] */
        Page_AgentCallResponse_: {
            /** Items */
            items: components["schemas"]["AgentCallResponse"][];
            /** Total */
            total: number;
        };
        /** Page[IngredientListItem] */
        Page_IngredientListItem_: {
            /** Items */
            items: components["schemas"]["IngredientListItem"][];
            /** Total */
            total: number;
        };
        /** Page[PublicRecipeSummaryResponse] */
        Page_PublicRecipeSummaryResponse_: {
            /** Items */
            items: components["schemas"]["PublicRecipeSummaryResponse"][];
            /** Total */
            total: number;
        };
        /** Page[RecipeRevisionSummary] */
        Page_RecipeRevisionSummary_: {
            /** Items */
            items: components["schemas"]["RecipeRevisionSummary"][];
            /** Total */
            total: number;
        };
        /** Page[RecipeSummaryResponse] */
        Page_RecipeSummaryResponse_: {
            /** Items */
            items: components["schemas"]["RecipeSummaryResponse"][];
            /** Total */
            total: number;
        };
        /** Page[SecurityEventResponse] */
        Page_SecurityEventResponse_: {
            /** Items */
            items: components["schemas"]["SecurityEventResponse"][];
            /** Total */
            total: number;
        };
        /** Page[StepImageResponse] */
        Page_StepImageResponse_: {
            /** Items */
            items: components["schemas"]["StepImageResponse"][];
            /** Total */
            total: number;
        };
        /** Page[WebhookDeliveryResponse] */
        Page_WebhookDeliveryResponse_: {
            /** Items */
            items: components["schemas"]["WebhookDeliveryResponse"][];
            /** Total */
            total: number;
        };
        /**
         * PasskeyConfirmation
         * @description An assertion over a challenge from `POST /api/v1/auth/login/passkey/options`.
         */
        PasskeyConfirmation: {
            /** Challenge Token */
            challenge_token: string;
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
        };
        /** PasskeyLoginRequest */
        PasskeyLoginRequest: {
            /** Challenge Token */
            challenge_token: string;
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
        };
        /** PasskeyOptionsResponse */
        PasskeyOptionsResponse: {
            /** Options */
            options: {
                [key: string]: unknown;
            };
            /** Challenge Token */
            challenge_token: string;
        };
        /** PasskeyResponse */
        PasskeyResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Last Used At */
            last_used_at: string | null;
            /** Backed Up */
            backed_up: boolean;
        };
        /** PasswordConfirmationRequest */
        PasswordConfirmationRequest: {
            /** Password */
            password: string;
        };
        /** PasswordLoginRequest */
        PasswordLoginRequest: {
            /** Login */
            login: string;
            /** Password */
            password: string;
        };
        /** PatCreatedResponse */
        PatCreatedResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Token Prefix */
            token_prefix: string;
            /** Permissions */
            permissions: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
            /** Token */
            token: string;
        };
        /** PatResponse */
        PatResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Token Prefix */
            token_prefix: string;
            /** Permissions */
            permissions: string[];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
        };
        /**
         * PeerChannelResponse
         * @description The peer channel in both directions. Sequence numbers count the
         *     events of one direction; the last delivery fields describe the last
         *     attempt to send to the peer, the receive fields the last catch-up with
         *     it. Error fields hold a short category, never the peer's text.
         */
        PeerChannelResponse: {
            /** Last Sent Seq */
            last_sent_seq: number;
            /** Out Seq */
            out_seq: number;
            /** Pending Outgoing */
            pending_outgoing: number;
            /** Last Received Seq */
            last_received_seq: number;
            /** Pending Incoming */
            pending_incoming: number;
            /** Last Delivery At */
            last_delivery_at: string | null;
            /** Last Delivery Status */
            last_delivery_status: number | null;
            /** Last Delivery Error */
            last_delivery_error: string | null;
            /** Next Send At */
            next_send_at: string | null;
            /** Last Catch Up At */
            last_catch_up_at: string | null;
            /** Last Reconcile At */
            last_reconcile_at: string | null;
            /** Last Receive Error */
            last_receive_error: string | null;
        };
        /** PeerInvitationResponse */
        PeerInvitationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** PeerMappingResponse */
        PeerMappingResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Name */
            name: string;
            /** Action */
            action: ("map" | "plain" | "none") | null;
            /** Target Id */
            target_id: string | null;
            /** Target Name */
            target_name: string | null;
            /** Created Here */
            created_here: boolean;
            /** Matched By */
            matched_by: ("seed_key" | "decision") | null;
            /** Used By */
            used_by: number;
            /**
             * Updated
             * Format: date-time
             */
            updated: string;
        };
        /**
         * PeerRef
         * @description A paired instance, by its public id here.
         */
        PeerRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** PeerResponse */
        PeerResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Instance Id
             * Format: uuid
             */
            instance_id: string;
            /** Name */
            name: string;
            /** Base Url */
            base_url: string;
            /** App Version */
            app_version: string;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "revoked";
            /** Revoked By */
            revoked_by: ("local" | "remote") | null;
            /** Protocol Version */
            protocol_version: number;
            /** Format Versions */
            format_versions: {
                [key: string]: number;
            };
            /** Capabilities */
            capabilities: string[];
            /** Users May Share */
            users_may_share: boolean;
            /** Accept Incoming */
            accept_incoming: boolean;
            /**
             * Mirror Visibility
             * @enum {string}
             */
            mirror_visibility: "instance" | "group";
            /** Mirror Group */
            mirror_group: string | null;
            /** Sync All */
            sync_all: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Paired At
             * Format: date-time
             */
            paired_at: string;
            /** Revoked At */
            revoked_at: string | null;
            /** Last Contact At */
            last_contact_at: string | null;
            channel?: components["schemas"]["PeerChannelResponse"] | null;
        };
        /** PeerRevokeResponse */
        PeerRevokeResponse: {
            peer: components["schemas"]["PeerResponse"];
            /** Peer Notified */
            peer_notified: boolean;
        };
        /**
         * PeerSuggestionGroupResponse
         * @description Every suggestion for one local entry. `warning` is true when an
         *     allergen or diet marker suggestion is among them.
         */
        PeerSuggestionGroupResponse: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment";
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Warning */
            warning: boolean;
            /** Suggestions */
            suggestions: components["schemas"]["PeerSuggestionResponse"][];
        };
        /**
         * PeerSuggestionRequest
         * @description Names one suggestion: the peer, the kind, the entry's public id at
         *     the peer and the field.
         */
        PeerSuggestionRequest: {
            /**
             * Peer Id
             * Format: uuid
             */
            peer_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "unit" | "tag" | "ingredient" | "equipment";
            /** Source Id */
            source_id: string;
            /** Field */
            field: string;
        };
        /**
         * PeerSuggestionResponse
         * @description One field of a local entry with the value a paired instance offers.
         *     Field names and values follow the catalogue file and the reference data
         *     updates; references are shown by name and conversions as unit code to
         *     grams. Other names and conversions show the local value joined with the
         *     peer's.
         */
        PeerSuggestionResponse: {
            peer: components["schemas"]["PeerRef"];
            /** Source Id */
            source_id: string;
            /** Field */
            field: string;
            /** Current */
            current: unknown;
            /** Suggested */
            suggested: unknown;
            /** Unmapped Units */
            unmapped_units: string[];
        };
        /** PeerSwitchesRequest */
        PeerSwitchesRequest: {
            /** Users May Share */
            users_may_share: boolean;
            /** Accept Incoming */
            accept_incoming: boolean;
            /**
             * Mirror Visibility
             * @enum {string}
             */
            mirror_visibility: "instance" | "group";
            /** Mirror Group */
            mirror_group?: string | null;
            /** Sync All */
            sync_all: boolean;
        };
        /** PermissionResponse */
        PermissionResponse: {
            /** Name */
            name: string;
            /** Grantable To Tokens */
            grantable_to_tokens: boolean;
        };
        /** PersonRef */
        PersonRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
            /** Avatar Id */
            avatar_id?: string | null;
        };
        /** PrivacyAcknowledgeRequest */
        PrivacyAcknowledgeRequest: {
            /** Version */
            version: number;
        };
        /** PrivacyAcknowledgementEntry */
        PrivacyAcknowledgementEntry: {
            user: components["schemas"]["UserSummaryResponse"];
            /** Version */
            version: number | null;
            /** Acknowledged At */
            acknowledged_at: string | null;
        };
        /**
         * PrivacyAcknowledgementOverviewResponse
         * @description Who acknowledged the current privacy statement version and who is
         *     still asked, among the active people (service accounts are never asked).
         *     Before the first statement both lists are empty.
         */
        PrivacyAcknowledgementOverviewResponse: {
            /** Current Version */
            current_version: number | null;
            /** Acknowledged */
            acknowledged: components["schemas"]["PrivacyAcknowledgementEntry"][];
            /** Pending */
            pending: components["schemas"]["PrivacyAcknowledgementEntry"][];
        };
        /** PrivacyModeResponse */
        PrivacyModeResponse: {
            /** Mode */
            mode: string;
            /** Default Visibility */
            default_visibility: string;
            /**
             * Allow Public Recipes
             * @default false
             */
            allow_public_recipes: boolean;
        };
        /** PrivacySettingsSchema */
        PrivacySettingsSchema: {
            /**
             * Default Recipe Visibility
             * @enum {string}
             */
            default_recipe_visibility: "private" | "household" | "shared" | "instance" | "peers" | "public";
            /** Users May Change Visibility */
            users_may_change_visibility: boolean;
            /**
             * Allow Public Recipes
             * @default false
             */
            allow_public_recipes: boolean;
            /**
             * Index Public Recipes
             * @default false
             */
            index_public_recipes: boolean;
        };
        /** PrivacyStatusResponse */
        PrivacyStatusResponse: {
            /** Current Version */
            current_version: number | null;
            /** Acknowledged Version */
            acknowledged_version: number | null;
            /** Pending */
            pending: boolean;
        };
        /** PublicBannerResponse */
        PublicBannerResponse: {
            severity: components["schemas"]["BannerSeverity"];
            /** Message */
            message: string;
            /** Locale */
            locale: string;
            /** Dismissible */
            dismissible: boolean;
            /** Ends At */
            ends_at: string | null;
            /** Key */
            key: string;
        };
        /** PublicEquipmentNeed */
        PublicEquipmentNeed: {
            /** Name */
            name: string;
            /** Count */
            count: number | null;
        };
        /**
         * PublicInfoResponse
         * @description What the login page needs before anybody signed in.
         */
        PublicInfoResponse: {
            /** Instance Name */
            instance_name: string;
            default_language: components["schemas"]["Language"];
            /** Version */
            version: string;
            /** Accent Color */
            accent_color: string;
            /** Login Background Key */
            login_background_key: string | null;
            /** Login Steam */
            login_steam: boolean;
            unit_system: components["schemas"]["UnitSystem"];
            date_format: components["schemas"]["DateFormat"];
            time_format: components["schemas"]["TimeFormat"];
            first_day_of_week: components["schemas"]["Weekday"];
            maintenance: components["schemas"]["PublicMaintenanceResponse"];
            features: components["schemas"]["FeatureSettingsSchema"];
            /** Privacy Mode */
            privacy_mode: string;
            /** Default Recipe Visibility */
            default_recipe_visibility: string;
            /** Imprint Published */
            imprint_published: boolean;
            /** Privacy Statement Published */
            privacy_statement_published: boolean;
            /** Allow Public Recipes */
            allow_public_recipes: boolean;
            /** Index Public Recipes */
            index_public_recipes: boolean;
        };
        /** PublicIngredientLine */
        PublicIngredientLine: {
            /** Name */
            name: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["PublicUnit"] | null;
            /**
             * Note
             * @default
             */
            note: string;
            sub_recipe?: components["schemas"]["PublicSubRecipe"] | null;
        };
        /** PublicMaintenanceResponse */
        PublicMaintenanceResponse: {
            /** Enabled */
            enabled: boolean;
            /** Message */
            message: string | null;
            /** Since */
            since: string | null;
        };
        /** PublicNutrition */
        PublicNutrition: {
            total: components["schemas"]["NutritionSchema"];
            per_serving: components["schemas"]["NutritionSchema"];
            /** Complete */
            complete: boolean;
            /** Extended */
            extended: components["schemas"]["ExtendedNutrientAmount"][];
        };
        /** PublicRecipeDetailResponse */
        PublicRecipeDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Description Text */
            description_text: string;
            /** Locale */
            locale: string;
            /** Available Locales */
            available_locales: string[];
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Base Servings */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes: number | null;
            /** Cook Minutes */
            cook_minutes: number | null;
            /** Rest Minutes */
            rest_minutes: number | null;
            /** Total Minutes */
            total_minutes: number | null;
            /** Difficulty */
            difficulty: string;
            /** Tags */
            tags: components["schemas"]["PublicTag"][];
            /** Allergens */
            allergens: string[];
            /** Diets */
            diets: string[];
            /** Season Months */
            season_months: number[];
            /** In Season */
            in_season: boolean;
            /** Author */
            author: string | null;
            /**
             * Author Avatar
             * @default false
             */
            author_avatar: boolean;
            /** Published At */
            published_at: string | null;
            /** Description */
            description: string;
            /** Tips */
            tips: string;
            /** Yield Amount */
            yield_amount: number | null;
            yield_unit: components["schemas"]["PublicUnit"] | null;
            /** Servings */
            servings: number;
            /** Ingredients */
            ingredients: components["schemas"]["PublicIngredientLine"][];
            /** Needs */
            needs: components["schemas"]["PublicSubRecipeNeed"][];
            /** Equipment */
            equipment: components["schemas"]["PublicEquipmentNeed"][];
            /** Steps */
            steps: components["schemas"]["PublicStep"][];
            nutrition: components["schemas"]["PublicNutrition"];
            /** Source Name */
            source_name: string | null;
            /** Source Url */
            source_url: string | null;
        };
        /** PublicRecipeSummaryResponse */
        PublicRecipeSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Description Text */
            description_text: string;
            /** Locale */
            locale: string;
            /** Available Locales */
            available_locales: string[];
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Base Servings */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes: number | null;
            /** Cook Minutes */
            cook_minutes: number | null;
            /** Rest Minutes */
            rest_minutes: number | null;
            /** Total Minutes */
            total_minutes: number | null;
            /** Difficulty */
            difficulty: string;
            /** Tags */
            tags: components["schemas"]["PublicTag"][];
            /** Allergens */
            allergens: string[];
            /** Diets */
            diets: string[];
            /** Season Months */
            season_months: number[];
            /** In Season */
            in_season: boolean;
            /** Author */
            author: string | null;
            /**
             * Author Avatar
             * @default false
             */
            author_avatar: boolean;
            /** Published At */
            published_at: string | null;
        };
        /**
         * PublicStep
         * @description A step. Mentions in `text` are rewritten for the visitor: an
         *     ingredient or equipment item carries its current name and the zero id, a
         *     public sub-recipe its title and public id, and a sub-recipe the visitor
         *     may not see the name `?` and the zero id, which the page shows as a
         *     placeholder.
         */
        PublicStep: {
            /** Position */
            position: number;
            /** Text */
            text: string;
            /** Duration Minutes */
            duration_minutes: number | null;
            /** Image Id */
            image_id: string | null;
            /** Ingredients */
            ingredients: components["schemas"]["PublicIngredientLine"][];
            /** Equipment */
            equipment: components["schemas"]["PublicStepEquipment"][];
        };
        /** PublicStepEquipment */
        PublicStepEquipment: {
            /** Name */
            name: string;
            /** Count */
            count: number | null;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /**
         * PublicSubRecipe
         * @description A recipe used inside another. One the visitor may not see comes
         *     without id and title, and still counts for allergens and nutrition.
         */
        PublicSubRecipe: {
            /** Id */
            id: string | null;
            /** Title */
            title: string | null;
            /** Accessible */
            accessible: boolean;
            /** Cover Image Id */
            cover_image_id: string | null;
        };
        /** PublicSubRecipeNeed */
        PublicSubRecipeNeed: {
            sub_recipe: components["schemas"]["PublicSubRecipe"];
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["PublicUnit"] | null;
            /** Batches */
            batches: number;
        };
        /** PublicTag */
        PublicTag: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Color */
            color: string | null;
        };
        /** PublicUnit */
        PublicUnit: {
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Plural Name */
            plural_name: string;
            /** Abbreviation */
            abbreviation: string;
        };
        /** RatingRequest */
        RatingRequest: {
            /** Stars */
            stars: number;
            /**
             * Comment
             * @default
             */
            comment: string;
            /** Variation Id */
            variation_id?: string | null;
        };
        /** RatingResponse */
        RatingResponse: {
            /** Stars */
            stars: number;
            /** Comment */
            comment: string;
            /** Rating Average */
            rating_average: number | null;
            /** Rating Count */
            rating_count: number;
        };
        /** RatingStatsResponse */
        RatingStatsResponse: {
            /** Rating Average */
            rating_average: number | null;
            /** Rating Count */
            rating_count: number;
        };
        /** ReceivedInvitationResponse */
        ReceivedInvitationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            household: components["schemas"]["HouseholdRef"];
            inviter: components["schemas"]["PersonRef"] | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** RecipeCopyResponse */
        RecipeCopyResponse: {
            recipe: components["schemas"]["RecipeRef"];
            owner: components["schemas"]["PersonRef"] | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** RecipeDeletionImpact */
        RecipeDeletionImpact: {
            /** Blocked */
            blocked: boolean;
            /** Used By */
            used_by: components["schemas"]["RecipeRef"][];
            /** Used By Hidden Count */
            used_by_hidden_count: number;
        };
        /** RecipeDetailResponse */
        RecipeDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Description Text */
            description_text: string;
            /** Locale */
            locale: string;
            /** Original Locale */
            original_locale: string;
            /** Available Locales */
            available_locales: string[];
            /** Status */
            status: string;
            /** Visibility */
            visibility: string;
            /** Effective Visibility */
            effective_visibility: string;
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Base Servings */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes: number | null;
            /** Cook Minutes */
            cook_minutes: number | null;
            /** Rest Minutes */
            rest_minutes: number | null;
            /** Total Minutes */
            total_minutes: number | null;
            /** Difficulty */
            difficulty: string;
            /** Tags */
            tags: components["schemas"]["TagRef"][];
            /** Allergens */
            allergens: string[];
            /** Diets */
            diets: string[];
            /** Rating Average */
            rating_average: number | null;
            /** Rating Count */
            rating_count: number;
            /** Is Favourite */
            is_favourite: boolean;
            /** Has Warning */
            has_warning: boolean;
            /** Unsuitable For Guests */
            unsuitable_for_guests: boolean;
            /** Season Months */
            season_months: number[];
            /** In Season */
            in_season: boolean;
            /** Missing Equipment */
            missing_equipment: components["schemas"]["EquipmentRef"][] | null;
            /** Kitchen Ready */
            kitchen_ready: boolean | null;
            /** Variation Count */
            variation_count: number;
            /** Variation Fits Guests */
            variation_fits_guests: boolean;
            /** Variation Fits Diets */
            variation_fits_diets: boolean;
            /** Can Edit */
            can_edit: boolean;
            owner: components["schemas"]["PersonRef"] | null;
            /** Created Via */
            created_via: string;
            /** Last Cooked */
            last_cooked: string | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            mirror?: components["schemas"]["MirrorSourceRef"] | null;
            /**
             * Peer Capped
             * @default false
             */
            peer_capped: boolean;
            /** Tips */
            tips: string;
            /** Yield Amount */
            yield_amount: number | null;
            yield_unit: components["schemas"]["UnitRef"] | null;
            /** Needs */
            needs: components["schemas"]["SubRecipeNeed"][];
            /** Equipment */
            equipment: components["schemas"]["EquipmentNeed"][];
            /** Source Url */
            source_url: string | null;
            /** Source Name */
            source_name: string | null;
            /** Servings */
            servings: number;
            /** Ingredients */
            ingredients: components["schemas"]["IngredientAmount"][];
            /** Steps */
            steps: components["schemas"]["StepView"][];
            nutrition: components["schemas"]["NutritionView"];
            /** Warnings */
            warnings: components["schemas"]["WarningView"][];
            own_rating: components["schemas"]["OwnRating"] | null;
            /** Own Note */
            own_note: string | null;
            /** Last Cooked By Me */
            last_cooked_by_me: string | null;
            /** Can Delete */
            can_delete: boolean;
            based_on: components["schemas"]["BasedOnRef"] | null;
            /** Based On Count */
            based_on_count: number;
            /** Rating Overall Average */
            rating_overall_average: number | null;
            /** Rating Overall Count */
            rating_overall_count: number;
            mirror_details?: components["schemas"]["MirrorView"] | null;
            /** Source Allergens Added */
            source_allergens_added?: string[];
            /** Unknown Allergens */
            unknown_allergens?: string[];
            /** Unknown Diet Markers */
            unknown_diet_markers?: string[];
            /** Unconfirmed Ingredient Ids */
            unconfirmed_ingredient_ids?: string[];
        };
        /**
         * RecipeEditResponse
         * @description The recipe as the editor works on it: every language, every id.
         */
        RecipeEditResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Original Locale */
            original_locale: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["RecipeTextSchema"];
            };
            /** Base Servings */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes: number | null;
            /** Cook Minutes */
            cook_minutes: number | null;
            /** Rest Minutes */
            rest_minutes: number | null;
            /** Difficulty */
            difficulty: string;
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Source Url */
            source_url: string | null;
            /** Source Name */
            source_name: string | null;
            /** Tag Ids */
            tag_ids: string[];
            /** Steps */
            steps: components["schemas"]["StepEdit"][];
            /** Ingredients */
            ingredients: components["schemas"]["StepIngredientEdit"][];
            /** Yield Amount */
            yield_amount: number | null;
            /** Yield Unit Id */
            yield_unit_id: string | null;
            /** Less Visible Sub Recipe Ids */
            less_visible_sub_recipe_ids: string[];
            /** Visibility */
            visibility: string;
            /** Effective Visibility */
            effective_visibility: string;
            /** Shared User Ids */
            shared_user_ids: string[];
            /** Shared Group Ids */
            shared_group_ids: string[];
            /** Shared Peers */
            shared_peers?: components["schemas"]["PeerRef"][];
            /**
             * Peer Capped
             * @default false
             */
            peer_capped: boolean;
            /** Peer Hidden Sub Recipe Ids */
            peer_hidden_sub_recipe_ids?: string[];
            /** Can Change Visibility */
            can_change_visibility: boolean;
            /** Created Via */
            created_via: string;
            owner: components["schemas"]["PersonRef"] | null;
            /** Can Edit */
            can_edit: boolean;
            /** Can Delete */
            can_delete: boolean;
            /** Co Editors */
            co_editors: components["schemas"]["PersonRef"][];
            /** Can Manage Co Editors */
            can_manage_co_editors: boolean;
            based_on: components["schemas"]["BasedOnRef"] | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /** Published At */
            published_at: string | null;
        };
        /** RecipeImportPreviewResponse */
        RecipeImportPreviewResponse: {
            /** Recipes */
            recipes: components["schemas"]["ImportPreviewRecipeResponse"][];
        };
        /** RecipeImportResponse */
        RecipeImportResponse: {
            /** Recipes */
            recipes: components["schemas"]["ImportedRecipeResponse"][];
            /** Created Ingredients */
            created_ingredients: string[];
            /** Created Equipment */
            created_equipment: string[];
            /** Matched Ingredients */
            matched_ingredients: number;
            /** Matched Equipment */
            matched_equipment: number;
            /** Conflicts */
            conflicts: components["schemas"]["ImportConflictResponse"][];
        };
        /** RecipeRef */
        RecipeRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Status */
            status: string;
        };
        /** RecipeRequest */
        RecipeRequest: {
            original_locale: components["schemas"]["ContentLocale"];
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["RecipeTextSchema"];
            };
            /**
             * Base Servings
             * @default 4
             */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes?: number | null;
            /** Cook Minutes */
            cook_minutes?: number | null;
            /** Rest Minutes */
            rest_minutes?: number | null;
            /** @default easy */
            difficulty: components["schemas"]["Difficulty"];
            /** Cover Image Id */
            cover_image_id?: string | null;
            /** Source Url */
            source_url?: string | null;
            /** Source Name */
            source_name?: string | null;
            /** Tag Ids */
            tag_ids?: string[];
            /** Steps */
            steps?: components["schemas"]["StepRequest"][];
            /** Ingredients */
            ingredients?: components["schemas"]["StepIngredientRequest"][];
            /** Yield Amount */
            yield_amount?: number | null;
            /** Yield Unit Id */
            yield_unit_id?: string | null;
            visibility?: components["schemas"]["RecipeVisibility"] | null;
            /** Shared User Ids */
            shared_user_ids?: string[] | null;
            /** Shared Group Ids */
            shared_group_ids?: string[] | null;
            /** Shared Peer Ids */
            shared_peer_ids?: string[] | null;
            /** Revision Note */
            revision_note?: string | null;
        };
        /**
         * RecipeRevisionResponse
         * @description The revision with its snapshot: the editable recipe in the shape of
         *     `RecipeEditResponse` (by public id, without status, visibility and
         *     shares) plus `schema_version` and `names`, the display names per locale
         *     of every referenced ingredient, unit, tag, equipment item and
         *     sub-recipe at that moment, by kind and public id.
         */
        RecipeRevisionResponse: {
            /** Number */
            number: number;
            /** Kind */
            kind: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Created Via */
            created_via: string;
            author: components["schemas"]["PersonRef"] | null;
            /** Note */
            note: string | null;
            /** Restored From */
            restored_from: number | null;
            credited_author?: components["schemas"]["PersonRef"] | null;
            /** Snapshot */
            snapshot: {
                [key: string]: unknown;
            };
        };
        /** RecipeRevisionSummary */
        RecipeRevisionSummary: {
            /** Number */
            number: number;
            /** Kind */
            kind: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Created Via */
            created_via: string;
            author: components["schemas"]["PersonRef"] | null;
            /** Note */
            note: string | null;
            /** Restored From */
            restored_from: number | null;
            credited_author?: components["schemas"]["PersonRef"] | null;
        };
        /** RecipeSummaryResponse */
        RecipeSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Description Text */
            description_text: string;
            /** Locale */
            locale: string;
            /** Original Locale */
            original_locale: string;
            /** Available Locales */
            available_locales: string[];
            /** Status */
            status: string;
            /** Visibility */
            visibility: string;
            /** Effective Visibility */
            effective_visibility: string;
            /** Cover Image Id */
            cover_image_id: string | null;
            /** Base Servings */
            base_servings: number;
            /** Prep Minutes */
            prep_minutes: number | null;
            /** Cook Minutes */
            cook_minutes: number | null;
            /** Rest Minutes */
            rest_minutes: number | null;
            /** Total Minutes */
            total_minutes: number | null;
            /** Difficulty */
            difficulty: string;
            /** Tags */
            tags: components["schemas"]["TagRef"][];
            /** Allergens */
            allergens: string[];
            /** Diets */
            diets: string[];
            /** Rating Average */
            rating_average: number | null;
            /** Rating Count */
            rating_count: number;
            /** Is Favourite */
            is_favourite: boolean;
            /** Has Warning */
            has_warning: boolean;
            /** Unsuitable For Guests */
            unsuitable_for_guests: boolean;
            /** Season Months */
            season_months: number[];
            /** In Season */
            in_season: boolean;
            /** Missing Equipment */
            missing_equipment: components["schemas"]["EquipmentRef"][] | null;
            /** Kitchen Ready */
            kitchen_ready: boolean | null;
            /** Variation Count */
            variation_count: number;
            /** Variation Fits Guests */
            variation_fits_guests: boolean;
            /** Variation Fits Diets */
            variation_fits_diets: boolean;
            /** Can Edit */
            can_edit: boolean;
            owner: components["schemas"]["PersonRef"] | null;
            /** Created Via */
            created_via: string;
            /** Last Cooked */
            last_cooked: string | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            mirror?: components["schemas"]["MirrorSourceRef"] | null;
            /**
             * Peer Capped
             * @default false
             */
            peer_capped: boolean;
        };
        /** RecipeTextSchema */
        RecipeTextSchema: {
            /** Title */
            title: string;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Tips
             * @default
             */
            tips: string;
        };
        /**
         * RecipeVisibility
         * @description Who may read a published recipe besides its owner, narrowest first. A
         *     draft is always its owner's alone.
         * @enum {string}
         */
        RecipeVisibility: "private" | "household" | "shared" | "instance" | "peers" | "public";
        /**
         * ReferenceUpdateResponse
         * @description A seed update an edit holds back: the field's current value, the
         *     seed's new value and the value the seed wrote before.
         */
        ReferenceUpdateResponse: {
            /** Kind */
            kind: string;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Field */
            field: string;
            /** Current */
            current: unknown;
            /** Seed */
            seed: unknown;
            /** Base */
            base: unknown;
        };
        /** RegisterPasskeyRequest */
        RegisterPasskeyRequest: {
            /** Challenge Token */
            challenge_token: string;
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
            /**
             * Name
             * @default Passkey
             */
            name: string;
        };
        /** RemovedLineView */
        RemovedLineView: {
            /** Change Id */
            change_id: string;
            /** Ingredient Id */
            ingredient_id: string | null;
            sub_recipe: components["schemas"]["SubRecipeRef"] | null;
            /** Name */
            name: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
        };
        /** RemovedResponse */
        RemovedResponse: {
            /** Removed */
            removed: number;
        };
        /** RenamePasskeyRequest */
        RenamePasskeyRequest: {
            /** Name */
            name: string;
        };
        /**
         * ResolvedPublicIdResponse
         * @description What a public id opens: the kind of page, the public id of its row
         *     (a step's recipe for a step) and the frontend path.
         */
        ResolvedPublicIdResponse: {
            /** Kind */
            kind: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Route */
            route: string;
        };
        /**
         * ResourceUsageResponse
         * @description How often each resource is used. Tags, units and equipment count the
         *     recipes the viewer may see that use them, each recipe once; categories
         *     and families count the ingredients in them. Every item is listed, zero
         *     included.
         */
        ResourceUsageResponse: {
            /** Tags */
            tags: components["schemas"]["UsageCount"][];
            /** Units */
            units: components["schemas"]["UsageCount"][];
            /** Categories */
            categories: components["schemas"]["UsageCount"][];
            /** Families */
            families: components["schemas"]["UsageCount"][];
            /** Equipment */
            equipment: components["schemas"]["UsageCount"][];
        };
        /** RestoreStepResponse */
        RestoreStepResponse: {
            /** Text */
            text: string;
            /** Command */
            command: string | null;
        };
        /**
         * RestrictionKind
         * @enum {string}
         */
        RestrictionKind: "allergy" | "intolerance" | "diet";
        /** RetentionSettingsSchema */
        RetentionSettingsSchema: {
            /** Security Log Days */
            security_log_days: number;
            /** Agent Calls Days */
            agent_calls_days: number;
            /** Webhook Deliveries Days */
            webhook_deliveries_days: number;
            /** Recipe Revisions Days */
            recipe_revisions_days: number;
        };
        /**
         * SecurityEventOutcome
         * @enum {string}
         */
        SecurityEventOutcome: "success" | "failure";
        /** SecurityEventResponse */
        SecurityEventResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Event Type */
            event_type: string;
            /** Outcome */
            outcome: string;
            /** Actor Id */
            actor_id: string | null;
            /** Actor Name */
            actor_name: string | null;
            /** Target User Id */
            target_user_id: string | null;
            /** Target Name */
            target_name: string | null;
            /** Detail */
            detail: {
                [key: string]: unknown;
            };
            /** Client Ip */
            client_ip: string | null;
            /** User Agent */
            user_agent: string | null;
        };
        /**
         * SecurityEventType
         * @enum {string}
         */
        SecurityEventType: "login" | "login_throttled" | "logout" | "password_confirmation" | "session_revoked" | "user_created" | "user_changed" | "user_deleted" | "user_deactivated" | "user_reactivated" | "user_permissions_changed" | "user_groups_changed" | "user_forced_logout" | "group_created" | "group_changed" | "group_deleted" | "pat_created" | "pat_revoked" | "api_key_created" | "api_key_revoked" | "password_changed" | "totp_enabled" | "totp_disabled" | "totp_reset" | "trusted_device_revoked" | "passkey_added" | "passkey_removed" | "settings_changed" | "peer_invitation_created" | "peer_invitation_revoked" | "peer_paired" | "peer_pairing_refused" | "peer_changed" | "peer_revoked" | "peer_auth_failed" | "oauth_client_registered" | "oauth_grant_approved" | "oauth_grant_denied" | "oauth_grant_revoked" | "oauth_token_reused";
        /** SecuritySettingsSchema */
        SecuritySettingsSchema: {
            /** Enforce Totp */
            enforce_totp: boolean;
            /** Min Password Length */
            min_password_length: number;
            /** Session Timeout Minutes */
            session_timeout_minutes: number;
            /** Session Max Lifetime Days */
            session_max_lifetime_days: number;
            /** Totp Trusted Device Days */
            totp_trusted_device_days: number;
            /** Max Login Attempts */
            max_login_attempts: number;
            /** Lockout Duration Minutes */
            lockout_duration_minutes: number;
            /** Enable Api Key Auth */
            enable_api_key_auth: boolean;
            /** Token Max Lifetime Days */
            token_max_lifetime_days: number;
        };
        /**
         * SelfDeletionImpact
         * @description What deleting the own account does, computed for this user and this
         *     instance. Backups keep the data until they rotate out.
         */
        SelfDeletionImpact: {
            /** Recipes Kept Online */
            recipes_kept_online: number;
            /** Recipes To Household */
            recipes_to_household: number;
            /** Recipes Deleted */
            recipes_deleted: number;
            /** Drafts Deleted */
            drafts_deleted: number;
            /** Recipes Handed Over */
            recipes_handed_over: components["schemas"]["HandedOverRecipe"][];
            /** Sub Recipes Kept Online */
            sub_recipes_kept_online: number;
            if_public_deleted: components["schemas"]["SelfDeletionRecipeFates"] | null;
            /** Can Delete Public Recipes */
            can_delete_public_recipes: boolean;
            /** Ingredients Kept */
            ingredients_kept: number;
            /** Lists Handed Over */
            lists_handed_over: number;
            /** Lists Deleted */
            lists_deleted: number;
            /** In Household */
            in_household: boolean;
            /** Refused Reason */
            refused_reason: ("system_user" | "last_admin") | null;
            /** Backup Keep Days */
            backup_keep_days: number;
            /**
             * Backups Clear By
             * Format: date
             */
            backups_clear_by: string;
        };
        /**
         * SelfDeletionRecipeFates
         * @description What happens to the own recipes when the user deletes the public
         *     recipes too, in the fields of the same names in `SelfDeletionImpact`.
         */
        SelfDeletionRecipeFates: {
            /** Recipes Deleted */
            recipes_deleted: number;
            /** Drafts Deleted */
            drafts_deleted: number;
            /** Recipes Handed Over */
            recipes_handed_over: components["schemas"]["HandedOverRecipe"][];
            /** Sub Recipes Kept Online */
            sub_recipes_kept_online: number;
        };
        /**
         * SelfDeletionRequest
         * @description Confirms the deletion with the own e-mail address and either the
         *     password or a passkey assertion.
         */
        SelfDeletionRequest: {
            /** Email */
            email: string;
            /** Password */
            password?: string | null;
            passkey?: components["schemas"]["PasskeyConfirmation"] | null;
            /**
             * Delete Public Recipes
             * @default false
             */
            delete_public_recipes: boolean;
        };
        /** SentInvitationResponse */
        SentInvitationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            invitee: components["schemas"]["PersonRef"] | null;
            inviter: components["schemas"]["PersonRef"] | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** ServiceReadingResponse */
        ServiceReadingResponse: {
            /** Name */
            name: string;
            /** Status */
            status: string;
            /** Latency Ms */
            latency_ms: number | null;
            /** Version */
            version: string | null;
            /** Detail */
            detail: string | null;
        };
        /** SessionResponse */
        SessionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Last Seen At
             * Format: date-time
             */
            last_seen_at: string;
            /** User Agent */
            user_agent: string | null;
            /** Client Ip */
            client_ip: string | null;
            /** Current */
            current: boolean;
        };
        /** ShoppingItemRequest */
        ShoppingItemRequest: {
            /** Ingredient Id */
            ingredient_id?: string | null;
            /**
             * Text
             * @default
             */
            text: string;
            /** Amount */
            amount?: number | null;
            /** Unit Id */
            unit_id?: string | null;
        };
        /** ShoppingItemResponse */
        ShoppingItemResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Name */
            name: string;
            /** Text */
            text: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            category: components["schemas"]["CategoryRef"] | null;
            /** Family Id */
            family_id: string | null;
            /** Checked */
            checked: boolean;
            checked_by: components["schemas"]["PersonRef"] | null;
            /** Checked At */
            checked_at: string | null;
            recipe: components["schemas"]["RecipeRef"] | null;
            /** Recipes */
            recipes: components["schemas"]["SubRecipeRef"][];
            /** Sub Recipe Path */
            sub_recipe_path: components["schemas"]["SubRecipeRef"][];
            /** Has Warning */
            has_warning: boolean;
        };
        /**
         * ShoppingItemUpdate
         * @description Only the fields sent change; send amount or unit_id as null to clear.
         */
        ShoppingItemUpdate: {
            /** Checked */
            checked?: boolean | null;
            /** Text */
            text?: string | null;
            /** Amount */
            amount?: number | null;
            /** Unit Id */
            unit_id?: string | null;
        };
        /**
         * ShoppingListMode
         * @description How a shopping list treats what was bought and how long it lives.
         * @enum {string}
         */
        ShoppingListMode: "continuous" | "normal";
        /**
         * ShoppingListNoteResponse
         * @description An idle list the viewer was on deleted itself.
         */
        ShoppingListNoteResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** List Name */
            list_name: string;
            /** Idle Days */
            idle_days: number;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /** ShoppingListRequest */
        ShoppingListRequest: {
            /** Name */
            name: string;
            /** Member Ids */
            member_ids?: string[];
        };
        /** ShoppingListResponse */
        ShoppingListResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            owner: components["schemas"]["PersonRef"] | null;
            /** Members */
            members: components["schemas"]["PersonRef"][];
            /** Is Owner */
            is_owner: boolean;
            /** Open Count */
            open_count: number;
            /** Checked Count */
            checked_count: number;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            mode: components["schemas"]["ShoppingListMode"];
            /** Keep */
            keep: boolean;
            /**
             * Last Activity At
             * Format: date-time
             */
            last_activity_at: string;
            /** Deletes On */
            deletes_on: string | null;
            /** Bought Window Hours */
            bought_window_hours: number;
            /** Items */
            items: components["schemas"]["ShoppingItemResponse"][];
        };
        /** ShoppingListSummaryResponse */
        ShoppingListSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            owner: components["schemas"]["PersonRef"] | null;
            /** Members */
            members: components["schemas"]["PersonRef"][];
            /** Is Owner */
            is_owner: boolean;
            /** Open Count */
            open_count: number;
            /** Checked Count */
            checked_count: number;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            mode: components["schemas"]["ShoppingListMode"];
            /** Keep */
            keep: boolean;
            /**
             * Last Activity At
             * Format: date-time
             */
            last_activity_at: string;
            /** Deletes On */
            deletes_on: string | null;
        };
        /**
         * ShoppingListUpdate
         * @description Only the fields sent change. Anyone on the list renames it and
         *     switches mode and keep; only the owner changes the members.
         */
        ShoppingListUpdate: {
            /** Name */
            name?: string | null;
            /** Member Ids */
            member_ids?: string[] | null;
            mode?: components["schemas"]["ShoppingListMode"] | null;
            /** Keep */
            keep?: boolean | null;
        };
        /** ShoppingSettingsSchema */
        ShoppingSettingsSchema: {
            /** Bought Window Hours */
            bought_window_hours: number;
            /** Idle List Days */
            idle_list_days: number;
        };
        /**
         * StaleStepView
         * @description A step the variation names that changed (`changed`) or went
         *     (`deleted`) since the revision it is based on, with its text then.
         */
        StaleStepView: {
            /** Step */
            step: number;
            /** State */
            state: string;
            /** Old Text */
            old_text: string;
            /** Current Text */
            current_text: string | null;
        };
        /** StepEdit */
        StepEdit: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["StepTextSchema"];
            };
            /** Duration Minutes */
            duration_minutes: number | null;
            /** Image Id */
            image_id: string | null;
            /** Ingredients */
            ingredients: components["schemas"]["StepIngredientEdit"][];
            /** Equipment */
            equipment: components["schemas"]["StepEquipmentEdit"][];
        };
        /** StepEquipmentEdit */
        StepEquipmentEdit: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Equipment Id
             * Format: uuid
             */
            equipment_id: string;
            /** Equipment Name */
            equipment_name: string;
            /** Count */
            count: number | null;
            /** Notes */
            notes: {
                [key: string]: components["schemas"]["NoteTextSchema"];
            };
        };
        /** StepEquipmentRequest */
        StepEquipmentRequest: {
            /** Id */
            id?: string | null;
            /**
             * Equipment Id
             * Format: uuid
             */
            equipment_id: string;
            /** Count */
            count?: number | null;
            /** Notes */
            notes?: {
                [key: string]: components["schemas"]["NoteTextSchema"];
            };
        };
        /** StepEquipmentView */
        StepEquipmentView: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            equipment: components["schemas"]["EquipmentRef"];
            /** Count */
            count: number | null;
            /** Note */
            note: string;
        };
        /**
         * StepImageResponse
         * @description An image a step of a visible recipe shows, offered for another step.
         *     `step_number` counts from 1 and `step_text` is that step's text in the
         *     viewer's language without marks or mentions. `matches` counts the
         *     ingredients and equipment items the step shares with the step being
         *     edited.
         */
        StepImageResponse: {
            /**
             * Image Id
             * Format: uuid
             */
            image_id: string;
            recipe: components["schemas"]["RecipeRef"];
            /** Step Number */
            step_number: number;
            /** Step Text */
            step_text: string;
            /** Matches */
            matches: number;
        };
        /** StepIngredientEdit */
        StepIngredientEdit: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Sub Recipe Id */
            sub_recipe_id: string | null;
            /** Ingredient Name */
            ingredient_name: string;
            /** Amount */
            amount: number | null;
            /** Unit Id */
            unit_id: string | null;
            /** Notes */
            notes: {
                [key: string]: components["schemas"]["NoteTextSchema"];
            };
        };
        /**
         * StepIngredientRequest
         * @description A catalogue ingredient or a sub-recipe, exactly one. A sub-recipe's
         *     amount is in its yield unit (scaled by amount / yield) or, without one,
         *     in servings of the sub-recipe.
         */
        StepIngredientRequest: {
            /** Id */
            id?: string | null;
            /** Ingredient Id */
            ingredient_id?: string | null;
            /** Sub Recipe Id */
            sub_recipe_id?: string | null;
            /** Amount */
            amount?: number | null;
            /** Unit Id */
            unit_id?: string | null;
            /** Notes */
            notes?: {
                [key: string]: components["schemas"]["NoteTextSchema"];
            };
        };
        /**
         * StepMarkerView
         * @description What differs in one step of the applied recipe; `position` matches
         *     `recipe.steps[].position`, `origin_step` is the original's number
         *     (null for a step the variation adds).
         */
        StepMarkerView: {
            /** Position */
            position: number;
            /** Origin Step */
            origin_step: number | null;
            /** Added */
            added: boolean;
            /** Text Changed */
            text_changed: boolean;
            /** Changed */
            changed: boolean;
            /** Change Ids */
            change_ids: string[];
            /** Lines */
            lines: components["schemas"]["LineMarkerView"][];
            /** Removed */
            removed: components["schemas"]["RemovedLineView"][];
        };
        /** StepRequest */
        StepRequest: {
            /** Id */
            id?: string | null;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["StepTextSchema"];
            };
            /** Duration Minutes */
            duration_minutes?: number | null;
            /** Image Id */
            image_id?: string | null;
            /** Ingredients */
            ingredients?: components["schemas"]["StepIngredientRequest"][];
            /** Equipment */
            equipment?: components["schemas"]["StepEquipmentRequest"][];
        };
        /** StepTextSchema */
        StepTextSchema: {
            /** Text */
            text: string;
        };
        /** StepView */
        StepView: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Position */
            position: number;
            /** Text */
            text: string;
            /** Duration Minutes */
            duration_minutes: number | null;
            /** Image Id */
            image_id: string | null;
            /** Ingredients */
            ingredients: components["schemas"]["IngredientAmount"][];
            /** Equipment */
            equipment: components["schemas"]["StepEquipmentView"][];
        };
        /** StorageStatusResponse */
        StorageStatusResponse: {
            /** Provider */
            provider: string;
            /** Provider Reachable */
            provider_reachable: boolean;
            database: components["schemas"]["DatabaseReadingResponse"];
            files: components["schemas"]["FileReadingResponse"];
            backups: components["schemas"]["BackupReadingResponse"];
            /** Warnings */
            warnings: string[];
            /** Backup Now Available */
            backup_now_available: boolean;
            /** Backup Requested */
            backup_requested: boolean;
            last_run: components["schemas"]["BackupRunStatusResponse"] | null;
        };
        /** StoredFileResponse */
        StoredFileResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** File Name */
            file_name: string;
            /** Content Type */
            content_type: string;
            /** Size */
            size: number;
            /** Width */
            width: number | null;
            /** Height */
            height: number | null;
            /** Has Thumbnail */
            has_thumbnail: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
        };
        /**
         * SubRecipeNeed
         * @description A sub-recipe the recipe needs: the line's amount scaled to the
         *     servings, and how many batches of the sub-recipe that is.
         */
        SubRecipeNeed: {
            sub_recipe: components["schemas"]["SubRecipeRef"];
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            /** Batches */
            batches: number;
        };
        /**
         * SubRecipeRef
         * @description A recipe used inside another. A sub-recipe the viewer may not see
         *     comes without id and title ("a recipe you don't have access to"), and
         *     still counts for allergens and nutrition.
         */
        SubRecipeRef: {
            /** Id */
            id: string | null;
            /** Title */
            title: string | null;
            /** Accessible */
            accessible: boolean;
            /** Total Minutes */
            total_minutes: number | null;
            /** Cover Image Id */
            cover_image_id: string | null;
        };
        /**
         * SuggestionReason
         * @description Why the meal plan suggests a recipe: the signal that weighed most in
         *     its score (`meal_suggestions.score`).
         * @enum {string}
         */
        SuggestionReason: "often_cooked" | "not_cooked_lately" | "favourite" | "in_season" | "cooked_this_time_last_year" | "fits_slot" | "new_recipe" | "not_cooked_yet" | "cooked_before";
        /** TableSizeResponse */
        TableSizeResponse: {
            /** Name */
            name: string;
            /** Bytes */
            bytes: number;
        };
        /**
         * TagKind
         * @description Diets are no tag kind: they are derived from the ingredients' diet
         *     markers.
         * @enum {string}
         */
        TagKind: "meal" | "cuisine" | "occasion" | "other";
        /** TagRef */
        TagRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Color */
            color: string | null;
        };
        /** TagRequest */
        TagRequest: {
            kind: components["schemas"]["TagKind"];
            /** Color */
            color?: string | null;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** TagResponse */
        TagResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Seeded */
            seeded: boolean;
            /** Kind */
            kind: string;
            /** Color */
            color: string | null;
            /** Name */
            name: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["NameTextSchema"];
            };
        };
        /** TestMailRequest */
        TestMailRequest: {
            /** To */
            to?: string | null;
        };
        /**
         * ThemePreset
         * @enum {string}
         */
        ThemePreset: "Aura" | "Lara" | "Material" | "Nora";
        /**
         * ThemePrimary
         * @enum {string}
         */
        ThemePrimary: "cuisine" | "soul" | "red" | "orange" | "emerald" | "green" | "lime" | "amber" | "yellow" | "teal" | "cyan" | "sky" | "blue" | "indigo" | "violet" | "purple" | "fuchsia" | "pink" | "rose";
        /**
         * ThemeSurface
         * @enum {string}
         */
        ThemeSurface: "neutral" | "slate" | "gray" | "zinc" | "stone" | "soho" | "viva" | "ocean";
        /**
         * TimeFormat
         * @enum {string}
         */
        TimeFormat: "24h" | "12h";
        /** TokenCreateRequest */
        TokenCreateRequest: {
            /** Name */
            name: string;
            /** Permissions */
            permissions?: string[];
            /** Expires At */
            expires_at?: string | null;
        };
        /** TotpConfirmRequest */
        TotpConfirmRequest: {
            /** Code */
            code: string;
        };
        /** TotpConfirmResponse */
        TotpConfirmResponse: {
            /** Session Started */
            session_started: boolean;
        };
        /** TotpEnrolRequest */
        TotpEnrolRequest: {
            /** Password */
            password?: string | null;
        };
        /** TotpEnrolmentResponse */
        TotpEnrolmentResponse: {
            /** Secret */
            secret: string;
            /** Provisioning Uri */
            provisioning_uri: string;
        };
        /** TotpLoginRequest */
        TotpLoginRequest: {
            /** Partial Token */
            partial_token: string;
            /** Code */
            code: string;
            /**
             * Trust Device
             * @default false
             */
            trust_device: boolean;
        };
        /**
         * TranslationRequest
         * @description One language of a recipe: its text, each step's text in order and,
         *     optionally, each step ingredient's note per step and each declared
         *     ingredient line's note in order.
         */
        TranslationRequest: {
            locale: components["schemas"]["ContentLocale"];
            text: components["schemas"]["RecipeTextSchema"];
            /** Steps */
            steps?: components["schemas"]["StepTextSchema"][];
            /** Notes */
            notes?: components["schemas"]["NoteTextSchema"][][] | null;
            /** Ingredient Notes */
            ingredient_notes?: components["schemas"]["NoteTextSchema"][] | null;
        };
        /** TrustedDeviceResponse */
        TrustedDeviceResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** User Agent */
            user_agent: string | null;
            /** Last Used At */
            last_used_at: string | null;
        };
        /** UnitDeletionImpact */
        UnitDeletionImpact: {
            /** Seeded */
            seeded: boolean;
            /** In Use */
            in_use: boolean;
        };
        /**
         * UnitKind
         * @enum {string}
         */
        UnitKind: "mass" | "volume" | "count" | "other";
        /** UnitRef */
        UnitRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Code */
            code: string;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Plural Name */
            plural_name: string;
            /** Abbreviation */
            abbreviation: string;
        };
        /** UnitRequest */
        UnitRequest: {
            /** Code */
            code: string;
            kind: components["schemas"]["UnitKind"];
            /** To Base */
            to_base?: number | null;
            /**
             * Sort Order
             * @default 0
             */
            sort_order: number;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["UnitTextSchema"];
            };
        };
        /** UnitResponse */
        UnitResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Seeded */
            seeded: boolean;
            /** Code */
            code: string;
            /** Kind */
            kind: string;
            /** To Base */
            to_base: number | null;
            /** Sort Order */
            sort_order: number;
            /** Name */
            name: string;
            /** Plural Name */
            plural_name: string;
            /** Abbreviation */
            abbreviation: string;
            /** Translations */
            translations: {
                [key: string]: components["schemas"]["UnitTextSchema"];
            };
        };
        /**
         * UnitSystem
         * @enum {string}
         */
        UnitSystem: "metric";
        /** UnitTextSchema */
        UnitTextSchema: {
            /** Name */
            name: string;
            /**
             * Plural Name
             * @default
             */
            plural_name: string;
            /**
             * Abbreviation
             * @default
             */
            abbreviation: string;
        };
        /** UpdateGroupRequest */
        UpdateGroupRequest: {
            /** Name */
            name?: string | null;
            /** Description */
            description?: string | null;
            /** Permissions */
            permissions?: string[] | null;
            /** Member Ids */
            member_ids?: string[] | null;
        };
        /** UpdateOwnProfileRequest */
        UpdateOwnProfileRequest: {
            /** Full Name */
            full_name?: string | null;
            /** Nickname */
            nickname?: string | null;
            /** Show Nickname */
            show_nickname?: boolean | null;
            /** Email */
            email?: string | null;
            language?: components["schemas"]["Language"] | null;
            theme_preset?: components["schemas"]["ThemePreset"] | null;
            theme_surface?: components["schemas"]["ThemeSurface"] | null;
            theme_primary?: components["schemas"]["ThemePrimary"] | null;
            /** Theme Dark Mode */
            theme_dark_mode?: boolean | null;
            amount_style?: components["schemas"]["AmountStyle"] | null;
            /** Share Restrictions With Hosts */
            share_restrictions_with_hosts?: boolean | null;
            /** Default Recipe Visibility */
            default_recipe_visibility?: ("private" | "household" | "shared" | "instance" | "peers" | "public") | null;
            /** Show Name On Public Recipes */
            show_name_on_public_recipes?: boolean | null;
            /** Show Name On Paired Instances */
            show_name_on_paired_instances?: boolean | null;
            /** Recipe Show Tips */
            recipe_show_tips?: boolean | null;
            /** Recipe Show Notes */
            recipe_show_notes?: boolean | null;
            /** Recipe Show Cooked */
            recipe_show_cooked?: boolean | null;
            /** Recipe Show Rating */
            recipe_show_rating?: boolean | null;
            /** Recipe Highlight Mentions */
            recipe_highlight_mentions?: boolean | null;
            /** Keep Screen On */
            keep_screen_on?: boolean | null;
            cook_mode_layout?: components["schemas"]["CookModeLayout"] | null;
        };
        /** UpdateUserRequest */
        UpdateUserRequest: {
            /** Full Name */
            full_name?: string | null;
            /** Nickname */
            nickname?: string | null;
            /** Show Nickname */
            show_nickname?: boolean | null;
            /** Email */
            email?: string | null;
            /** Password */
            password?: string | null;
            /** Permissions */
            permissions?: string[] | null;
            /** Group Ids */
            group_ids?: string[] | null;
            language?: components["schemas"]["Language"] | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UsageCount */
        UsageCount: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Usage Count */
            usage_count: number;
        };
        /** UserResponse */
        UserResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Full Name */
            full_name: string;
            /** Nickname */
            nickname: string | null;
            /** Show Nickname */
            show_nickname: boolean;
            /** Display Name */
            display_name: string;
            /** Email */
            email: string;
            /** Is Active */
            is_active: boolean;
            /** Is Systemuser */
            is_systemuser: boolean;
            /** Permissions */
            permissions: string[];
            /** Effective Permissions */
            effective_permissions: string[];
            /** Group Ids */
            group_ids: string[];
            language: components["schemas"]["Language"];
            /** Totp Enabled */
            totp_enabled: boolean;
            /** Totp Mandatory */
            totp_mandatory: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Last Logged In */
            last_logged_in: string | null;
            /** Avatar Id */
            avatar_id?: string | null;
        };
        /**
         * UserSummaryResponse
         * @description What every signed-in user may see of another account. The display
         *     name is the nickname when the person chose to go by it, otherwise the
         *     full name, which then stays private to the person and the admins.
         */
        UserSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Display Name */
            display_name: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * VariationChangeKind
         * @description One difference a recipe variation makes to the original.
         * @enum {string}
         */
        VariationChangeKind: "swap" | "add_line" | "remove_line" | "step_text" | "extra_step";
        /**
         * VariationChangeRequest
         * @description One change; which fields count depends on `kind`:
         *
         *     - `swap`: `ingredient_id` → `to_ingredient_id` in step `step`, or in every
         *       step with `step` null. `keep_amount` (default) keeps each line's amount,
         *       unit and note; otherwise `amount`, `unit_id` and `note` replace them.
         *     - `add_line`: `ingredient_id`, `amount`, `unit_id`, `note` in step `step`.
         *     - `remove_line`: the lines of step `step` naming `ingredient_id` or
         *       `sub_recipe_id`.
         *     - `step_text`: `text` instead of step `step`'s text.
         *     - `extra_step`: a new step after step `step` (0 puts it first) with
         *       `text`, `duration_minutes`, `lines` and `equipment`.
         *
         *     Steps are numbered from 1 as the recipe is now. `id` keeps an existing
         *     change's id on an update; leave it out for a new change.
         */
        VariationChangeRequest: {
            kind: components["schemas"]["VariationChangeKind"];
            /** Id */
            id?: string | null;
            /** Step */
            step?: number | null;
            /** Ingredient Id */
            ingredient_id?: string | null;
            /** Sub Recipe Id */
            sub_recipe_id?: string | null;
            /** To Ingredient Id */
            to_ingredient_id?: string | null;
            /** Amount */
            amount?: number | null;
            /** Unit Id */
            unit_id?: string | null;
            /**
             * Keep Amount
             * @default true
             */
            keep_amount: boolean;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Text
             * @default
             */
            text: string;
            /** Duration Minutes */
            duration_minutes?: number | null;
            /** Lines */
            lines?: components["schemas"]["VariationLineRequest"][];
            /** Equipment */
            equipment?: components["schemas"]["VariationEquipmentRequest"][];
        };
        /**
         * VariationChangeView
         * @description A stored change with the names of what it refers to, in the viewer's
         *     language. `available` is false when a record it names no longer
         *     exists; `applies` is false when its step or line is no longer in the
         *     recipe. Either way it is left out of the applied recipe.
         */
        VariationChangeView: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** Step */
            step: number | null;
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Ingredient Name */
            ingredient_name: string | null;
            sub_recipe: components["schemas"]["SubRecipeRef"] | null;
            /** To Ingredient Id */
            to_ingredient_id: string | null;
            /** To Ingredient Name */
            to_ingredient_name: string | null;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            /** Keep Amount */
            keep_amount: boolean;
            /** Note */
            note: string;
            /** Text */
            text: string;
            /** Duration Minutes */
            duration_minutes: number | null;
            /** Lines */
            lines: components["schemas"]["VariationLineView"][];
            /** Equipment */
            equipment: components["schemas"]["VariationEquipmentView"][];
            /** Available */
            available: boolean;
            /** Applies */
            applies: boolean;
        };
        /** VariationEquipmentRequest */
        VariationEquipmentRequest: {
            /**
             * Equipment Id
             * Format: uuid
             */
            equipment_id: string;
            /** Count */
            count?: number | null;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** VariationEquipmentView */
        VariationEquipmentView: {
            equipment: components["schemas"]["EquipmentRef"] | null;
            /** Count */
            count: number | null;
            /** Note */
            note: string;
        };
        /** VariationLineRequest */
        VariationLineRequest: {
            /**
             * Ingredient Id
             * Format: uuid
             */
            ingredient_id: string;
            /** Amount */
            amount?: number | null;
            /** Unit Id */
            unit_id?: string | null;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** VariationLineView */
        VariationLineView: {
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Ingredient Name */
            ingredient_name: string;
            /** Amount */
            amount: number | null;
            unit: components["schemas"]["UnitRef"] | null;
            /** Note */
            note: string;
        };
        /** VariationRef */
        VariationRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** VariationRequest */
        VariationRequest: {
            /** Name */
            name: string;
            /**
             * Note
             * @default
             */
            note: string;
            locale: components["schemas"]["ContentLocale"];
            /**
             * Private
             * @default false
             */
            private: boolean;
            /** Changes */
            changes?: components["schemas"]["VariationChangeRequest"][];
        };
        /** VariationResponse */
        VariationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Recipe Id
             * Format: uuid
             */
            recipe_id: string;
            /** Name */
            name: string;
            /** Note */
            note: string;
            /** Locale */
            locale: string;
            /** Private */
            private: boolean;
            author: components["schemas"]["PersonRef"] | null;
            /** Based On Revision */
            based_on_revision: number | null;
            /** Current Revision */
            current_revision: number | null;
            /** Is Stale */
            is_stale: boolean;
            /** Base Revision Available */
            base_revision_available: boolean;
            /** Stale Steps */
            stale_steps: components["schemas"]["StaleStepView"][];
            /** Changes */
            changes: components["schemas"]["VariationChangeView"][];
            /** Rating Average */
            rating_average: number | null;
            /** Rating Count */
            rating_count: number;
            own_rating: components["schemas"]["OwnRating"] | null;
            /** Can Edit */
            can_edit: boolean;
            /** Can Delete */
            can_delete: boolean;
            /** Can Adopt */
            can_adopt: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /**
             * Mirrored
             * @default false
             */
            mirrored: boolean;
            /** Source Author Name */
            source_author_name?: string | null;
            /** Source Author Avatar Id */
            source_author_avatar_id?: string | null;
        };
        /**
         * VariationViewResponse
         * @description The recipe with the variation applied, in the shape of the recipe
         *     detail: ingredient list, nutrition, allergens, diets, the viewer's
         *     warnings, the dinner-guest flag and the kitchen are derived from the
         *     applied recipe; the rating fields are the variation's.
         */
        VariationViewResponse: {
            recipe: components["schemas"]["RecipeDetailResponse"];
            variation: components["schemas"]["VariationResponse"];
            /** Steps */
            steps: components["schemas"]["StepMarkerView"][];
        };
        /** VersionResponse */
        VersionResponse: {
            /** Version */
            version: string;
        };
        /** WarningView */
        WarningView: {
            /**
             * Restriction Id
             * Format: uuid
             */
            restriction_id: string;
            /** Kind */
            kind: string;
            /** Allergen */
            allergen: string | null;
            /** Ingredient Id */
            ingredient_id: string | null;
            /** Diet */
            diet: string | null;
            /** Family Id */
            family_id: string | null;
            /** Ingredient Names */
            ingredient_names: string[];
        };
        /** WebAppIconResponse */
        WebAppIconResponse: {
            /** Src */
            src: string;
            /** Sizes */
            sizes: string;
            /** Type */
            type: string;
            /** Purpose */
            purpose: string;
        };
        /**
         * WebAppManifestResponse
         * @description The web app manifest (W3C Web Application Manifest) that lets a
         *     phone or a desktop browser install the instance as an app under its own
         *     name. Paths are absolute, since the manifest is served below /api while
         *     the app lives at the root.
         */
        WebAppManifestResponse: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Short Name */
            short_name: string;
            /** Lang */
            lang: string;
            /** Dir */
            dir: string;
            /** Start Url */
            start_url: string;
            /** Scope */
            scope: string;
            /** Display */
            display: string;
            /** Theme Color */
            theme_color: string;
            /** Background Color */
            background_color: string;
            /** Icons */
            icons: components["schemas"]["WebAppIconResponse"][];
        };
        /** WebhookDeliveryResponse */
        WebhookDeliveryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Event */
            event: string;
            /** Status */
            status: string;
            /** Attempts */
            attempts: number;
            /** Next Attempt At */
            next_attempt_at: string | null;
            /** Last Attempt At */
            last_attempt_at: string | null;
            /** Http Status */
            http_status: number | null;
            /** Duration Ms */
            duration_ms: number;
            /** Error */
            error: string | null;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
        };
        /** WebhookEventResponse */
        WebhookEventResponse: {
            /** Key */
            key: string;
            /** Description */
            description: string;
        };
        /**
         * WebhookSecretResponse
         * @description Answers create and rotate: the only time the secret is shown.
         */
        WebhookSecretResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Url */
            url: string;
            /** Events */
            events: string[];
            /** Enabled */
            enabled: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
            /** Secret */
            secret: string;
        };
        /** WebhookSubscriptionRequest */
        WebhookSubscriptionRequest: {
            /** Name */
            name: string;
            /** Url */
            url: string;
            /** Events */
            events: string[];
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        /** WebhookSubscriptionResponse */
        WebhookSubscriptionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Url */
            url: string;
            /** Events */
            events: string[];
            /** Enabled */
            enabled: boolean;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Changed
             * Format: date-time
             */
            changed: string;
        };
        /**
         * Weekday
         * @enum {string}
         */
        Weekday: "monday" | "saturday" | "sunday";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordLoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_totp_api_v1_auth_login_totp_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TotpLoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_options_api_v1_auth_login_passkey_options_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyOptionsResponse"];
                };
            };
        };
    };
    login_passkey_api_v1_auth_login_passkey_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasskeyLoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    read_me_api_v1_web_users_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentUserResponse"];
                };
            };
        };
    };
    delete_own_account_api_v1_web_users_me_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SelfDeletionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_me_api_v1_web_users_me_patch: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateOwnProfileRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentUserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    replace_avatar_api_v1_web_users_me_avatar_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_replace_avatar_api_v1_web_users_me_avatar_put"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentUserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_avatar_api_v1_web_users_me_avatar_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentUserResponse"];
                };
            };
        };
    };
    change_password_api_v1_web_users_me_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangePasswordRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    enroll_totp_api_v1_web_users_me_totp_enroll_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["TotpEnrolRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TotpEnrolmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    confirm_totp_api_v1_web_users_me_totp_confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TotpConfirmRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TotpConfirmResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    disable_totp_api_v1_web_users_me_totp_disable_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordConfirmationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_passkeys_api_v1_web_users_me_passkeys_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyResponse"][];
                };
            };
        };
    };
    register_passkey_api_v1_web_users_me_passkeys_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterPasskeyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    passkey_registration_options_api_v1_web_users_me_passkeys_options_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyOptionsResponse"];
                };
            };
        };
    };
    remove_passkey_api_v1_web_users_me_passkeys__passkey_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                passkey_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rename_passkey_api_v1_web_users_me_passkeys__passkey_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                passkey_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RenamePasskeyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasskeyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_sessions_api_v1_web_users_me_sessions_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"][];
                };
            };
        };
    };
    revoke_other_sessions_api_v1_web_users_me_sessions_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    read_current_session_api_v1_web_users_me_sessions_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentSessionResponse"];
                };
            };
        };
    };
    revoke_session_api_v1_web_users_me_sessions__session_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_trusted_devices_api_v1_web_users_me_trusted_devices_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TrustedDeviceResponse"][];
                };
            };
        };
    };
    revoke_all_trusted_devices_api_v1_web_users_me_trusted_devices_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    revoke_trusted_device_api_v1_web_users_me_trusted_devices__device_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                device_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_pats_api_v1_web_users_me_personal_access_tokens_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PatResponse"][];
                };
            };
        };
    };
    create_pat_api_v1_web_users_me_personal_access_tokens_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TokenCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PatCreatedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_pat_api_v1_web_users_me_personal_access_tokens__token_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_own_security_events_api_v1_web_users_me_security_events_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                event_type?: components["schemas"]["SecurityEventType"][] | null;
                outcome?: components["schemas"]["SecurityEventOutcome"] | null;
                date_from?: string | null;
                date_to?: string | null;
                sort?: "newest" | "oldest";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_SecurityEventResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_own_agent_call_tools_api_v1_web_users_me_agent_calls_tools_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string[];
                };
            };
        };
    };
    list_own_agent_calls_api_v1_web_users_me_agent_calls_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                tool?: string[] | null;
                outcome?: components["schemas"]["AgentCallOutcome"] | null;
                date_from?: string | null;
                date_to?: string | null;
                sort?: "newest" | "oldest";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_AgentCallResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_features_api_v1_web_settings_features_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeatureSettingsSchema"];
                };
            };
        };
    };
    save_features_api_v1_web_settings_features_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeatureSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeatureSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_retention_api_v1_web_settings_retention_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RetentionSettingsSchema"];
                };
            };
        };
    };
    save_retention_api_v1_web_settings_retention_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RetentionSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RetentionSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_backup_retention_api_v1_web_settings_backup_retention_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BackupRetentionResponse"];
                };
            };
        };
    };
    read_maintenance_api_v1_web_settings_maintenance_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MaintenanceResponse"];
                };
            };
        };
    };
    save_maintenance_api_v1_web_settings_maintenance_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MaintenanceRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MaintenanceResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_alerts_api_v1_web_settings_mail_alerts_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AlertResponse"][];
                };
            };
        };
    };
    list_mail_templates_api_v1_web_settings_mail_templates_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MailTemplateKindResponse"][];
                };
            };
        };
    };
    save_mail_templates_api_v1_web_settings_mail_templates__kind__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: components["schemas"]["MailTemplateKind"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    [key: string]: components["schemas"]["MailTemplateTextSchema"];
                };
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_mail_template_api_v1_web_settings_mail_templates__kind__preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: components["schemas"]["MailTemplateKind"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MailTemplateTextSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MailTemplatePreviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    default_mail_template_api_v1_web_settings_mail_templates__kind__default_get: {
        parameters: {
            query?: {
                locale?: "en-GB" | "de-AT";
            };
            header?: never;
            path: {
                kind: components["schemas"]["MailTemplateKind"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MailTemplateLocaleResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_mail_template_api_v1_web_settings_mail_templates__kind__import_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: components["schemas"]["MailTemplateKind"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_mail_template_api_v1_web_settings_mail_templates__kind__import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_mail_template_api_v1_web_settings_mail_templates__kind__export_get: {
        parameters: {
            query?: {
                locale?: "en-GB" | "de-AT";
            };
            header?: never;
            path: {
                kind: components["schemas"]["MailTemplateKind"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/html": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    back_up_now_api_v1_web_admin_backups_run_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    read_restore_guidance_api_v1_web_admin_backups_restore_guidance_get: {
        parameters: {
            query?: {
                locale?: "en-GB" | "de-AT";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RestoreStepResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_logs_api_v1_web_admin_logs_get: {
        parameters: {
            query?: {
                level?: string;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LogEntryResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_legal_versions_api_v1_web_admin_legal__kind__versions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: components["schemas"]["LegalKind"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LegalVersionResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_legal_page_api_v1_web_admin_legal__kind__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: components["schemas"]["LegalKind"];
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LegalPublishRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LegalPageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    privacy_statement_draft_api_v1_web_admin_legal_privacy_draft_get: {
        parameters: {
            query?: {
                locale?: "en-GB" | "de-AT";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LegalDraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    privacy_acknowledgements_api_v1_web_admin_legal_privacy_acknowledgements_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrivacyAcknowledgementOverviewResponse"];
                };
            };
        };
    };
    own_privacy_status_api_v1_web_users_me_privacy_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrivacyStatusResponse"];
                };
            };
        };
    };
    acknowledge_privacy_api_v1_web_users_me_privacy_acknowledge_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PrivacyAcknowledgeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decline_privacy_api_v1_web_users_me_privacy_decline_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    own_consents_api_v1_web_users_me_consents_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConsentResponse"][];
                };
            };
        };
    };
    grant_consent_api_v1_web_users_me_consents__kind__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConsentResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    withdraw_consent_api_v1_web_users_me_consents__kind__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConsentResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cooking_calendar_api_v1_web_cook_events_get: {
        parameters: {
            query: {
                date_from: string;
                date_to: string;
                user_id?: string | null;
                recipe_id?: string | null;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_cook_event_api_v1_web_cook_events_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CookEventRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recent_cook_events_api_v1_web_cook_events_recent_get: {
        parameters: {
            query?: {
                limit?: number;
                user_id?: string | null;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    on_this_day_api_v1_web_cook_events_on_this_day_get: {
        parameters: {
            query?: {
                date?: string | null;
                mine?: boolean;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    log_cook_once_api_v1_web_cook_events_once_put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CookOnceRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookOnceResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_cook_event_api_v1_web_cook_events__event_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CookEventUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_cook_event_api_v1_web_cook_events__event_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_meal_plan_api_v1_web_meal_plan_get: {
        parameters: {
            query: {
                date_from: string;
                date_to: string;
                scope?: components["schemas"]["MealPlanScope"] | null;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MealPlanEntryResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_meal_api_v1_web_meal_plan_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MealPlanRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MealPlanEntryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    suggest_meals_api_v1_web_meal_plan_suggestions_get: {
        parameters: {
            query: {
                date_from: string;
                date_to: string;
                scope?: components["schemas"]["MealPlanScope"] | null;
                slot?: components["schemas"]["MealSlot"] | null;
                limit?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MealPlanSuggestionResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_meal_api_v1_web_meal_plan__entry_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                entry_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MealPlanRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MealPlanEntryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_meal_api_v1_web_meal_plan__entry_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entry_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    meal_plan_to_shopping_list_api_v1_web_meal_plan_shopping_list_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MealPlanToListRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AddedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    home_api_v1_web_home_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HomeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_food_restrictions_api_v1_web_users_me_food_restrictions_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FoodRestrictionResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_food_restriction_api_v1_web_users_me_food_restrictions_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FoodRestrictionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FoodRestrictionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_food_restriction_api_v1_web_users_me_food_restrictions__restriction_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                restriction_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_own_data_api_v1_web_users_me_export_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The data as a file. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    own_deletion_impact_api_v1_web_users_me_deletion_impact_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SelfDeletionImpact"];
                };
            };
        };
    };
    account_deletion_impact_api_v1_web_users__user_id__deletion_impact_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AccountDeletionImpact"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_user_api_v1_web_users__user_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_user_api_v1_web_users__user_id__delete: {
        parameters: {
            query?: {
                /** @description The person who takes over the recipes and ingredients. */
                new_owner_id?: string | null;
                /** @description Without a new owner: keep the recipes' visibility, make them visible to every signed-in user (public recipes stay public), or delete them. Private and household recipes cannot keep theirs. */
                ownerless_visibility?: "keep" | "instance" | "delete";
            };
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user_api_v1_web_users__user_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateUserRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    user_directory_api_v1_web_users_directory_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DirectoryUserResponse"][];
                };
            };
        };
    };
    list_users_api_v1_web_users_get: {
        parameters: {
            query?: {
                /** @description At most this many users. */
                limit?: number | null;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_user_api_v1_web_users_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateUserRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_user_totp_api_v1_web_users__user_id__reset_totp_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    replace_user_avatar_api_v1_web_users__user_id__avatar_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_replace_user_avatar_api_v1_web_users__user_id__avatar_put"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_user_avatar_api_v1_web_users__user_id__avatar_delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    force_logout_user_api_v1_web_users__user_id__logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_permissions_api_v1_web_permissions_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PermissionResponse"][];
                };
            };
        };
    };
    group_directory_api_v1_web_groups_directory_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GroupSummaryResponse"][];
                };
            };
        };
    };
    list_groups_api_v1_web_groups_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GroupResponse"][];
                };
            };
        };
    };
    create_group_api_v1_web_groups_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateGroupRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GroupResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_group_api_v1_web_groups__group_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                group_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_group_api_v1_web_groups__group_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                group_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateGroupRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GroupResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_api_keys_api_v1_web_api_keys_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyResponse"][];
                };
            };
        };
    };
    create_api_key_api_v1_web_api_keys_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TokenCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiKeyCreatedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_api_key_api_v1_web_api_keys__key_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_security_events_api_v1_web_security_events_get: {
        parameters: {
            query?: {
                user_id?: string | null;
                limit?: number;
                offset?: number;
                event_type?: components["schemas"]["SecurityEventType"][] | null;
                outcome?: components["schemas"]["SecurityEventOutcome"] | null;
                date_from?: string | null;
                date_to?: string | null;
                sort?: "newest" | "oldest";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_SecurityEventResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_agent_calls_api_v1_web_agent_calls_get: {
        parameters: {
            query?: {
                user_id?: string | null;
                limit?: number;
                offset?: number;
                tool?: string[] | null;
                outcome?: components["schemas"]["AgentCallOutcome"] | null;
                date_from?: string | null;
                date_to?: string | null;
                sort?: "newest" | "oldest";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_AgentCallResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_agent_call_tools_api_v1_web_agent_calls_tools_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string[];
                };
            };
        };
    };
    read_general_api_v1_web_settings_general_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GeneralSettingsSchema"];
                };
            };
        };
    };
    save_general_api_v1_web_settings_general_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GeneralSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GeneralSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_security_api_v1_web_settings_security_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecuritySettingsSchema"];
                };
            };
        };
    };
    save_security_api_v1_web_settings_security_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SecuritySettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecuritySettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_mail_api_v1_web_settings_mail_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MailSettingsResponse"];
                };
            };
        };
    };
    save_mail_api_v1_web_settings_mail_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MailSettingsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MailSettingsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    send_test_mail_api_v1_web_settings_mail_test_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["TestMailRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_integrations_api_v1_web_settings_integrations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationSettingsResponse"];
                };
            };
        };
    };
    save_integrations_api_v1_web_settings_integrations_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IntegrationSettingsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationSettingsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_agents_api_v1_web_settings_agents_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentSettingsSchema"];
                };
            };
        };
    };
    save_agents_api_v1_web_settings_agents_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_privacy_api_v1_web_settings_privacy_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrivacySettingsSchema"];
                };
            };
        };
    };
    save_privacy_api_v1_web_settings_privacy_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PrivacySettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrivacySettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_shopping_api_v1_web_settings_shopping_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingSettingsSchema"];
                };
            };
        };
    };
    save_shopping_api_v1_web_settings_shopping_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShoppingSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_notifications_api_v1_web_settings_notifications_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationSettingsSchema"];
                };
            };
        };
    };
    save_notifications_api_v1_web_settings_notifications_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NotificationSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_banner_api_v1_web_settings_banner_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BannerSettingsSchema"];
                };
            };
        };
    };
    save_banner_api_v1_web_settings_banner_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BannerSettingsSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BannerSettingsSchema"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_host_api_v1_web_admin_host_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HostStatusResponse"];
                };
            };
        };
    };
    read_storage_api_v1_web_admin_storage_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StorageStatusResponse"];
                };
            };
        };
    };
    list_webhook_events_api_v1_web_admin_webhooks_events_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookEventResponse"][];
                };
            };
        };
    };
    list_webhooks_api_v1_web_admin_webhooks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookSubscriptionResponse"][];
                };
            };
        };
    };
    create_webhook_api_v1_web_admin_webhooks_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WebhookSubscriptionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookSecretResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_webhook_api_v1_web_admin_webhooks__webhook_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookSubscriptionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_webhook_api_v1_web_admin_webhooks__webhook_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WebhookSubscriptionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookSubscriptionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_webhook_api_v1_web_admin_webhooks__webhook_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rotate_webhook_secret_api_v1_web_admin_webhooks__webhook_id__rotate_secret_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookSecretResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    test_webhook_api_v1_web_admin_webhooks__webhook_id__test_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookDeliveryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_webhook_deliveries_api_v1_web_admin_webhooks__webhook_id__deliveries_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: never;
            path: {
                webhook_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_WebhookDeliveryResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_webhook_delivery_api_v1_web_admin_webhooks__webhook_id__deliveries__delivery_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                webhook_id: string;
                delivery_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WebhookDeliveryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_notices_api_v1_web_admin_notices_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoticeAdminResponse"][];
                };
            };
        };
    };
    create_notice_api_v1_web_admin_notices_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoticeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoticeAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_notice_api_v1_web_admin_notices__notice_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notice_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoticeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoticeAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_notice_api_v1_web_admin_notices__notice_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    notice_acknowledgements_api_v1_web_admin_notices__notice_id__acknowledgements_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcknowledgementOverviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pending_notices_api_v1_web_notices_pending_get: {
        parameters: {
            query?: {
                locale?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoticeResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    acknowledge_notice_api_v1_web_notices__notice_id__acknowledge_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_own_instance_api_v1_web_admin_peers_self_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OwnInstanceResponse"];
                };
            };
        };
    };
    list_peer_invitations_api_v1_web_admin_peers_invitations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerInvitationResponse"][];
                };
            };
        };
    };
    create_peer_invitation_api_v1_web_admin_peers_invitations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreatedPeerInvitationResponse"];
                };
            };
        };
    };
    revoke_peer_invitation_api_v1_web_admin_peers_invitations__invitation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invitation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_peer_invitation_api_v1_web_admin_peers_accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AcceptPeerInvitationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_peers_api_v1_web_admin_peers_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerResponse"][];
                };
            };
        };
    };
    update_peer_switches_api_v1_web_admin_peers__peer_id__switches_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PeerSwitchesRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_peer_api_v1_web_admin_peers__peer_id__refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_peer_api_v1_web_admin_peers__peer_id__revoke_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerRevokeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_peer_api_v1_web_admin_peers__peer_id__sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_file_api_v1_web_files_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_file_api_v1_web_files_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StoredFileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_file_api_v1_web_files__file_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                file_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StoredFileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_file_api_v1_web_files__file_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                file_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_file_content_api_v1_web_files__file_id__content_get: {
        parameters: {
            query?: {
                variant?: "original" | "thumbnail";
                disposition?: "inline" | "attachment";
            };
            header?: {
                "if-none-match"?: string | null;
            };
            path: {
                file_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": unknown;
                };
            };
            /** @description Not Modified */
            304: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Temporary Redirect */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resource_usage_api_v1_web_resources_usage_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceUsageResponse"];
                };
            };
        };
    };
    list_units_api_v1_web_units_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_unit_api_v1_web_units_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UnitRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_unit_api_v1_web_units__unit_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                unit_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UnitRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_unit_api_v1_web_units__unit_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                unit_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    unit_deletion_impact_api_v1_web_units__unit_id__deletion_impact_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                unit_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitDeletionImpact"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    merge_unit_api_v1_web_units__unit_id__merge_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                unit_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MergeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_tags_api_v1_web_tags_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_tag_api_v1_web_tags_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_tag_api_v1_web_tags__tag_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                tag_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_tag_api_v1_web_tags__tag_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                tag_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_families_api_v1_web_ingredient_families_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FamilyResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_family_api_v1_web_ingredient_families_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FamilyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FamilyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_family_api_v1_web_ingredient_families__family_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                family_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FamilyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FamilyResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_family_api_v1_web_ingredient_families__family_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                family_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_categories_api_v1_web_ingredient_categories_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_category_api_v1_web_ingredient_categories_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CategoryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_category_api_v1_web_ingredient_categories__category_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                category_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CategoryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_category_api_v1_web_ingredient_categories__category_id__delete: {
        parameters: {
            query?: {
                /** @description The category its ingredients move to; none leaves them uncategorised. */
                replacement_id?: string | null;
            };
            header?: never;
            path: {
                category_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    nutrition_sources_api_v1_web_nutrition_sources_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NutritionSourcesResponse"];
                };
            };
        };
    };
    list_reference_updates_api_v1_web_admin_reference_updates_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReferenceUpdateResponse"][];
                };
            };
        };
    };
    accept_reference_update_api_v1_web_admin_reference_updates_accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AcceptReferenceUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_catalogue_api_v1_web_admin_catalogue_export_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The catalogue file. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    preview_catalogue_import_api_v1_web_admin_catalogue_import_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_preview_catalogue_import_api_v1_web_admin_catalogue_import_preview_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CataloguePreviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_catalogue_api_v1_web_admin_catalogue_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_catalogue_api_v1_web_admin_catalogue_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CatalogueImportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_ingredients_api_v1_web_ingredients_get: {
        parameters: {
            query?: {
                search?: string | null;
                category_id?: string | null;
                family_id?: string | null;
                status?: components["schemas"]["IngredientStatus"] | null;
                mine?: boolean;
                /** @description At least this many recipes use it. */
                min_usage?: number | null;
                /** @description At most this many recipes use it. */
                max_usage?: number | null;
                /** @description `name` alphabetical or `usage` by usage count; without it a search ranks the best matches first and otherwise the order is alphabetical. */
                sort?: ("name" | "usage") | null;
                order?: "asc" | "desc";
                limit?: number;
                offset?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_IngredientListItem_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_ingredient_api_v1_web_ingredients_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IngredientRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ingredient_duplicates_api_v1_web_ingredients_duplicates_get: {
        parameters: {
            query: {
                name: string;
                /** @description Compare in this language only; both by default. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DuplicateCandidate"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_ingredient_api_v1_web_ingredients__ingredient_id__get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_ingredient_api_v1_web_ingredients__ingredient_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IngredientRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_ingredient_api_v1_web_ingredients__ingredient_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activate_ingredient_api_v1_web_ingredients__ingredient_id__activate_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ingredient_deletion_impact_api_v1_web_ingredients__ingredient_id__deletion_impact_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDeletionImpact"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    merge_ingredient_api_v1_web_ingredients__ingredient_id__merge_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                ingredient_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MergeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IngredientDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_extended_nutrients_api_v1_web_nutrition_nutrients_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExtendedNutrientResponse"][];
                };
            };
        };
    };
    search_usda_api_v1_web_nutrition_usda_search_get: {
        parameters: {
            query: {
                query: string;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FoodMatchResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_usda_food_api_v1_web_nutrition_usda__fdc_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fdc_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FoodMatchResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_equipment_api_v1_web_equipment_get: {
        parameters: {
            query?: {
                search?: string | null;
                kind?: components["schemas"]["EquipmentKind"] | null;
                status?: components["schemas"]["EquipmentStatus"] | null;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_equipment_api_v1_web_equipment_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EquipmentRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    equipment_duplicates_api_v1_web_equipment_duplicates_get: {
        parameters: {
            query: {
                name: string;
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentDuplicate"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_equipment_api_v1_web_equipment__equipment_id__get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_equipment_api_v1_web_equipment__equipment_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EquipmentRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_equipment_api_v1_web_equipment__equipment_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activate_equipment_api_v1_web_equipment__equipment_id__activate_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    equipment_deletion_impact_api_v1_web_equipment__equipment_id__deletion_impact_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentDeletionImpact"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    merge_equipment_api_v1_web_equipment__equipment_id__merge_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                equipment_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MergeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EquipmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_kitchen_api_v1_web_kitchen_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KitchenResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_kitchen_api_v1_web_kitchen_put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KitchenRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KitchenResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_kitchen_api_v1_web_kitchen_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    set_up_kitchen_api_v1_web_kitchen_setup_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KitchenSetupRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KitchenResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_recipe_api_v1_web_recipes__recipe_id__export_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The `.cui` file. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.cuisine.recipe+zip": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_recipes_api_v1_web_admin_recipes_export_get: {
        parameters: {
            query?: {
                /** @description The recipes to export; every recipe the caller may see without. */
                recipe_id?: string[] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The `.cui` file. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.cuisine.recipe+zip": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_import_api_v1_web_recipes_import_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_preview_import_api_v1_web_recipes_import_preview_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeImportPreviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_recipes_api_v1_web_recipes_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_recipes_api_v1_web_recipes_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeImportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_recipes_api_v1_web_recipes_get: {
        parameters: {
            query?: {
                search?: string | null;
                tag_id?: string[];
                status?: ("published" | "drafts") | null;
                mine?: boolean;
                favourites?: boolean;
                max_minutes?: number | null;
                difficulty?: components["schemas"]["Difficulty"] | null;
                ingredient_id?: string | null;
                /** @description Only recipes that fit every one of these diets. */
                diets?: components["schemas"]["Diet"][];
                /** @description User ids of dinner guests; sets unsuitable_for_guests on every recipe. */
                guests?: string[];
                hide_unsuitable_for_guests?: boolean;
                /** @description Only recipes in season this month (see season_months). */
                in_season?: boolean;
                /** @description Only recipes the viewer's kitchen has every item for; ignored before the kitchen is set up. */
                only_kitchen_ready?: boolean;
                sort?: "newest" | "title" | "changed";
                limit?: number;
                offset?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_RecipeSummaryResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_recipe_api_v1_web_recipes_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecipeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_step_images_api_v1_web_step_images_get: {
        parameters: {
            query?: {
                /** @description Ingredients of the step being edited; steps sharing them rank first. */
                ingredient_id?: string[];
                /** @description Equipment of the step being edited; steps sharing it rank first. */
                equipment_id?: string[];
                search?: string | null;
                limit?: number;
                offset?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_StepImageResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_recipe_api_v1_web_recipes__recipe_id__get: {
        parameters: {
            query?: {
                servings?: number | null;
                /** @description User ids of dinner guests; sets unsuitable_for_guests. */
                guests?: string[];
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_recipe_api_v1_web_recipes__recipe_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecipeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_recipe_api_v1_web_recipes__recipe_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_recipe_for_editing_api_v1_web_recipes__recipe_id__edit_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_recipe_translation_api_v1_web_recipes__recipe_id__translation_put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TranslationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_recipe_api_v1_web_recipes__recipe_id__publish_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    unpublish_recipe_api_v1_web_recipes__recipe_id__unpublish_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recipe_deletion_impact_api_v1_web_recipes__recipe_id__deletion_impact_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeDeletionImpact"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_favourite_api_v1_web_recipes__recipe_id__favourite_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FavouriteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rate_recipe_api_v1_web_recipes__recipe_id__rating_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RatingRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RatingResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_rating_api_v1_web_recipes__recipe_id__rating_delete: {
        parameters: {
            query?: {
                /** @description Removes the rating of this variation. */
                variation_id?: string | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RatingStatsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_note_api_v1_web_recipes__recipe_id__note_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recipe_cook_events_api_v1_web_recipes__recipe_id__cook_events_get: {
        parameters: {
            query?: {
                /** @description Only the viewer's own cook events. */
                mine?: boolean;
                /** @description At most this many, the newest. */
                limit?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CookEventResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_recipe_revisions_api_v1_web_recipes__recipe_id__revisions_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_RecipeRevisionSummary_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_recipe_revision_api_v1_web_recipes__recipe_id__revisions__number__get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                number: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeRevisionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_recipe_revision_api_v1_web_recipes__recipe_id__revisions__number__restore_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                number: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_variations_api_v1_web_recipes__recipe_id__variations_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VariationResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_variation_api_v1_web_recipes__recipe_id__variations_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VariationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VariationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_variation_api_v1_web_recipes__recipe_id__variations__variation_id__get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                variation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VariationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_variation_api_v1_web_recipes__recipe_id__variations__variation_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                variation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VariationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VariationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_variation_api_v1_web_recipes__recipe_id__variations__variation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recipe_id: string;
                variation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    view_variation_api_v1_web_recipes__recipe_id__variations__variation_id__view_get: {
        parameters: {
            query?: {
                servings?: number | null;
                /** @description User ids of dinner guests; sets recipe.unsuitable_for_guests. */
                guests?: string[];
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                variation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VariationViewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    adopt_variation_api_v1_web_recipes__recipe_id__variations__variation_id__adopt_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
                variation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdoptVariationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdoptVariationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_co_editors_api_v1_web_recipes__recipe_id__co_editors_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PersonRef"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_co_editors_api_v1_web_recipes__recipe_id__co_editors_put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CoEditorsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PersonRef"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    copy_recipe_api_v1_web_recipes__recipe_id__copy_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeEditResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_copies_api_v1_web_recipes__recipe_id__copies_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecipeCopyResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_peer_share_targets_api_v1_web_peers_share_targets_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerRef"][];
                };
            };
        };
    };
    list_incoming_recipes_api_v1_web_admin_incoming_recipes_get: {
        parameters: {
            query?: {
                status?: ("pending" | "rejected") | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncomingRecipeResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncomingRecipeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AcceptIncomingRecipeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcceptedRecipeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncomingRecipeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reopen_incoming_recipe_api_v1_web_admin_incoming_recipes__item_id__reopen_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncomingRecipeResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_waiting_recipes_api_v1_web_admin_peers__peer_id__incoming_recipes_accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcceptedWaitingResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_peer_mappings_api_v1_web_admin_peers__peer_id__mappings_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerMappingResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    correct_peer_mapping_api_v1_web_admin_peers__peer_id__mappings__kind___source_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                peer_id: string;
                kind: "unit" | "tag" | "ingredient" | "equipment";
                source_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MappingCorrectionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerMappingResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_peer_suggestions_api_v1_web_admin_peer_suggestions_get: {
        parameters: {
            query?: {
                peer_id?: string | null;
                kind?: ("unit" | "tag" | "ingredient" | "equipment") | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeerSuggestionGroupResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_peer_suggestion_api_v1_web_admin_peer_suggestions_accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PeerSuggestionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dismiss_peer_suggestion_api_v1_web_admin_peer_suggestions_dismiss_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PeerSuggestionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_shopping_lists_api_v1_web_shopping_lists_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListSummaryResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_shopping_list_api_v1_web_shopping_lists_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShoppingListRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_shopping_list_notes_api_v1_web_shopping_lists_notes_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListNoteResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dismiss_shopping_list_note_api_v1_web_shopping_lists_notes__note_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_shopping_list_api_v1_web_shopping_lists__list_id__get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_shopping_list_api_v1_web_shopping_lists__list_id__put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShoppingListUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_shopping_list_api_v1_web_shopping_lists__list_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    leave_shopping_list_api_v1_web_shopping_lists__list_id__leave_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_shopping_item_api_v1_web_shopping_lists__list_id__items_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShoppingItemRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_shopping_item_api_v1_web_shopping_lists__list_id__items__item_id__delete: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                list_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_shopping_item_api_v1_web_shopping_lists__list_id__items__item_id__patch: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                list_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShoppingItemUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShoppingListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    clear_checked_items_api_v1_web_shopping_lists__list_id__clear_checked_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RemovedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_recipe_to_list_api_v1_web_shopping_lists__list_id__recipes_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddRecipeToListRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AddedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    shopping_list_events_api_v1_web_shopping_lists__list_id__events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                list_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    my_household_api_v1_web_households_mine_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MyHouseholdResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rename_household_api_v1_web_households_mine_put: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HouseholdRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HouseholdResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_household_api_v1_web_households_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HouseholdRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HouseholdResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    leave_household_api_v1_web_households_mine_leave_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    invite_to_household_api_v1_web_households_mine_invitations_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InviteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SentInvitationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_invitation_api_v1_web_households_mine_invitations__invitation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invitation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    my_invitations_api_v1_web_households_invitations_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReceivedInvitationResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_invitation_api_v1_web_households_invitations__invitation_id__accept_post: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                invitation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HouseholdResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decline_invitation_api_v1_web_households_invitations__invitation_id__decline_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                invitation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    household_memberships_api_v1_web_admin_households_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the user's UI language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HouseholdMembershipResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resolve_public_id_api_v1_web_resolve__public_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                public_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResolvedPublicIdResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    inspect_authorization_api_v1_web_oauth_authorize_inspect_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AuthorizationRequestSchema"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthorizationPromptResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decide_authorization_api_v1_web_oauth_authorize_decision_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AuthorizationDecisionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthorizationDecisionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_connected_apps_api_v1_web_users_me_connected_apps_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectedAppResponse"][];
                };
            };
        };
    };
    revoke_connected_app_api_v1_web_users_me_connected_apps__app_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    public_info_api_v1_public_info_get: {
        parameters: {
            query?: {
                locale?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicInfoResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    public_robots_api_v1_public_robots_txt_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
        };
    };
    public_manifest_api_v1_public_manifest_webmanifest_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/manifest+json": components["schemas"]["WebAppManifestResponse"];
                };
            };
        };
    };
    public_banner_api_v1_public_banner_get: {
        parameters: {
            query?: {
                locale?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicBannerResponse"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    public_login_background_api_v1_public_branding_login_background_get: {
        parameters: {
            query?: never;
            header?: {
                "if-none-match"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/webp": unknown;
                };
            };
            /** @description Not Modified */
            304: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Temporary Redirect */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_legal_page_api_v1_public_legal__kind__get: {
        parameters: {
            query?: {
                locale?: "en-GB" | "de-AT";
            };
            header?: never;
            path: {
                kind: components["schemas"]["LegalKind"];
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LegalPageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_public_recipes_api_v1_public_recipes_get: {
        parameters: {
            query?: {
                search?: string | null;
                tag_id?: string[];
                /** @description Only recipes that fit every one of these diets. */
                diets?: components["schemas"]["Diet"][];
                max_minutes?: number | null;
                difficulty?: components["schemas"]["Difficulty"] | null;
                sort?: "newest" | "title";
                limit?: number;
                offset?: number;
                /** @description The language to read in; defaults to the instance's language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page_PublicRecipeSummaryResponse_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_public_recipe_tags_api_v1_public_recipes_tags_get: {
        parameters: {
            query?: {
                /** @description The language to read in; defaults to the instance's language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicTag"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_public_recipe_api_v1_public_recipes__recipe_id__get: {
        parameters: {
            query?: {
                servings?: number | null;
                /** @description The language to read in; defaults to the instance's language. */
                locale?: components["schemas"]["ContentLocale"] | null;
            };
            header?: never;
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublicRecipeDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_public_recipe_image_api_v1_public_recipes__recipe_id__images__image_id__get: {
        parameters: {
            query?: never;
            header?: {
                "if-none-match"?: string | null;
            };
            path: {
                recipe_id: string;
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/webp": unknown;
                };
            };
            /** @description Not Modified */
            304: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Temporary Redirect */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_public_recipe_author_avatar_api_v1_public_recipes__recipe_id__author_avatar_get: {
        parameters: {
            query?: never;
            header?: {
                "if-none-match"?: string | null;
            };
            path: {
                recipe_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/webp": unknown;
                };
            };
            /** @description Not Modified */
            304: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Temporary Redirect */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pat_version_api_v1_pat_version_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionResponse"];
                };
            };
        };
    };
    pat_me_api_v1_pat_users_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummaryResponse"];
                };
            };
        };
    };
    key_whoami_api_v1_key_whoami_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummaryResponse"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    ready_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
}
