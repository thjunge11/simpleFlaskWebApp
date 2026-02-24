--
-- PostgreSQL database dump
--

\restrict cLyakoj82uoAA3CxNNlWWUct8aDWejkPcbSgckcDGJHxis8x7UUVlIniFKYry6r

-- Dumped from database version 16.12 (Debian 16.12-1.pgdg13+1)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: category_tags; Type: TABLE; Schema: public; Owner: flaskapp
--

CREATE TABLE public.category_tags (
    tag_id integer NOT NULL,
    tag_name character varying(50)
);


ALTER TABLE public.category_tags OWNER TO flaskapp;

--
-- Name: categorie_tags_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: flaskapp
--

ALTER TABLE public.category_tags ALTER COLUMN tag_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.categorie_tags_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: game_category_tags; Type: TABLE; Schema: public; Owner: flaskapp
--

CREATE TABLE public.game_category_tags (
    tag_id integer NOT NULL,
    game_id integer NOT NULL
);


ALTER TABLE public.game_category_tags OWNER TO flaskapp;

--
-- Name: games; Type: TABLE; Schema: public; Owner: flaskapp
--

CREATE TABLE public.games (
    game_id bigint NOT NULL,
    name text NOT NULL,
    perspective_id integer NOT NULL,
    platform_id integer NOT NULL,
    finished boolean DEFAULT false NOT NULL,
    playtime numeric,
    release_year smallint,
    comments text,
    finished_at date
);


ALTER TABLE public.games OWNER TO flaskapp;

--
-- Name: history_game_id_seq; Type: SEQUENCE; Schema: public; Owner: flaskapp
--

ALTER TABLE public.games ALTER COLUMN game_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.history_game_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

--
-- Name: perspectives; Type: TABLE; Schema: public; Owner: flaskapp
--

CREATE TABLE public.perspectives (
    perspective_id integer NOT NULL,
    perspective_name character varying(50)
);


ALTER TABLE public.perspectives OWNER TO flaskapp;

--
-- Name: perspectives_perspective_id_seq; Type: SEQUENCE; Schema: public; Owner: flaskapp
--

ALTER TABLE public.perspectives ALTER COLUMN perspective_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.perspectives_perspective_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: platforms; Type: TABLE; Schema: public; Owner: flaskapp
--

CREATE TABLE public.platforms (
    platform_id integer NOT NULL,
    platform_name character varying(50)
);


ALTER TABLE public.platforms OWNER TO flaskapp;

--
-- Name: platforms_platform_id_seq; Type: SEQUENCE; Schema: public; Owner: flaskapp
--

ALTER TABLE public.platforms ALTER COLUMN platform_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.platforms_platform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: category_tags categorie_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.category_tags
    ADD CONSTRAINT categorie_tags_pkey PRIMARY KEY (tag_id);


--
-- Name: category_tags categorie_tags_tag_name_key; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.category_tags
    ADD CONSTRAINT categorie_tags_tag_name_key UNIQUE (tag_name);


--
-- Name: game_category_tags game_category_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.game_category_tags
    ADD CONSTRAINT game_category_tags_pkey PRIMARY KEY (tag_id, game_id);


--
-- Name: games history_pkey; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT history_pkey PRIMARY KEY (game_id);

--
-- Name: perspectives perspectives_pkey; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.perspectives
    ADD CONSTRAINT perspectives_pkey PRIMARY KEY (perspective_id);


--
-- Name: platforms platforms_pkey; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT platforms_pkey PRIMARY KEY (platform_id);


--
-- Name: perspectives unique_perspective_name; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.perspectives
    ADD CONSTRAINT unique_perspective_name UNIQUE (perspective_name);


--
-- Name: platforms unique_platform_name; Type: CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.platforms
    ADD CONSTRAINT unique_platform_name UNIQUE (platform_name);


--
-- Name: ix_history_index; Type: INDEX; Schema: public; Owner: flaskapp
--

CREATE INDEX ix_history_index ON public.games USING btree (game_id);


--
-- Name: game_category_tags game_category_tags_game_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.game_category_tags
    ADD CONSTRAINT game_category_tags_game_id_fkey FOREIGN KEY (game_id) REFERENCES public.games(game_id);


--
-- Name: game_category_tags game_category_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.game_category_tags
    ADD CONSTRAINT game_category_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.category_tags(tag_id);


--
-- Name: games history_perspective_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT history_perspective_id_fkey FOREIGN KEY (perspective_id) REFERENCES public.perspectives(perspective_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: games history_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: flaskapp
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT history_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.platforms(platform_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict cLyakoj82uoAA3CxNNlWWUct8aDWejkPcbSgckcDGJHxis8x7UUVlIniFKYry6r

