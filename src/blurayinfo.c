/*
 * This file code is based on code examples in libbluray library
 * Copyright (C) 2016 Taapat
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library. If not, see
 * <http://www.gnu.org/licenses/>.
 */

#include <Python.h>
#include <dirent.h>

#include <libbluray/bluray.h>

#include "mpls_parse.h"

typedef struct {
	uint32_t duration;
	char clip_id[125];
} titlelist;

static char *_mk_path(const char *base, const char *sub)
{
	size_t n1 = strlen(base);
	size_t n2 = strlen(sub);
	char *result = (char*)malloc(n1 + n2 + 2);
	strcpy(result, base);
	strcat(result, "/");
	strcat(result, sub);

	return result;
}

static uint32_t _pl_duration(MPLS_PL *pl)
{
	int ii;
	uint32_t duration = 0;
	MPLS_PI *pi;

	for (ii = 0; ii < pl->list_count; ii++) {
		pi = &pl->play_item[ii];
		duration += pi->out_time - pi->in_time;
	}

	return duration;
}

static int _filter_short(MPLS_PL *pl)
{
	if (_pl_duration(pl) / 45000 <= 180) {
		return 0;
	}

	return 1;
}

static int _find_repeats(MPLS_PL *pl, const char *m2ts)
{
	int ii, count = 0;

	for (ii = 0; ii < pl->list_count; ii++) {
		MPLS_PI *pi;
		pi = &pl->play_item[ii];
		if (strcmp(pi->clip[0].clip_id, m2ts) == 0) {
			count++;
		}
	}

	return count;
}

static int _filter_repeats(MPLS_PL *pl)
{
	int ii;

	for (ii = 0; ii < pl->list_count; ii++) {
		MPLS_PI *pi;
		pi = &pl->play_item[ii];
		/* Ignore titles with repeated segments */
		if (_find_repeats(pl, pi->clip[0].clip_id) > 2) {
			return 0;
		}
	}

	return 1;
}

static int _filter_dup(MPLS_PL *pl_list[], int count, MPLS_PL *pl)
{
	int ii, jj;

	for (ii = 0; ii < count; ii++) {
		if (pl->list_count != pl_list[ii]->list_count ||
			_pl_duration(pl) != _pl_duration(pl_list[ii])) {
			continue;
		}
		for (jj = 0; jj < pl->list_count; jj++) {
			MPLS_PI *pi1, *pi2;
			pi1 = &pl->play_item[jj];
			pi2 = &pl_list[ii]->play_item[jj];
			if (memcmp(pi1->clip[0].clip_id, pi2->clip[0].clip_id, 5) != 0 ||
				pi1->in_time != pi2->in_time ||
				pi1->out_time != pi2->out_time) {
				break;
			}
		}
		if (jj != pl->list_count) {
			continue;
		}
		return 0;
	}

	return 1;
}

static int _qsort_str_cmp(const void *a, const void *b)
{
	const char *stra = *(char * const *)a;
	const char *strb = *(char * const *)b;

	return strcmp(stra, strb);
}

static MPLS_PL* _process_file(char *name, MPLS_PL *pl_list[], int pl_count)
{
	MPLS_PL *pl = bd_read_mpls(name);

	if (pl == NULL) {
		fprintf(stderr, "[blurayinfo] Parse failed: %s\n", name);
		return NULL;
	}
	/* Ignore short playlists */
	if (!_filter_short(pl)) {
		bd_free_mpls(pl);
		return NULL;
	}
	/* Ignore titles with repeated segments */
	if (!_filter_repeats(pl)) {
		bd_free_mpls(pl);
		return NULL;
	}
	/* Ignore duplicate titles */
	if (!_filter_dup(pl_list, pl_count, pl)) {
		bd_free_mpls(pl);
		return NULL;
	}

	return pl;
}

static uint32_t _pl_chapter_count(MPLS_PL *pl)
{
	unsigned ii, chapters = 0;

	/* Count the number of "entry" marks (skipping "link" marks)
	   This is the the number of chapters */
	for (ii = 0; ii < pl->mark_count; ii++) {
		if (pl->play_mark[ii].mark_type == BD_MARK_ENTRY) {
			chapters++;
		}
	}

	return chapters;
}

static void _video_props(MPLS_STN *s, int *full_hd, int *mpeg12)
{
	unsigned ii;
	*mpeg12 = 1;
	*full_hd = 0;

	for (ii = 0; ii < s->num_video; ii++) {
		if (s->video[ii].coding_type > 4) {
			*mpeg12 = 0;
		}
		/* Video format 1080i or 1080p */
		if (s->video[ii].format == 4 || s->video[ii].format == 6) {
			*full_hd = 1;
		}
	}
}

static int _cmp_video_props(const MPLS_PL *p1, const MPLS_PL *p2)
{
	MPLS_STN *s1 = &p1->play_item[0].stn;
	MPLS_STN *s2 = &p2->play_item[0].stn;
	int fhd1, fhd2, mp12_1, mp12_2;

	_video_props(s1, &fhd1, &mp12_1);
	_video_props(s2, &fhd2, &mp12_2);

	/* Prefer Full HD over HD/SD */
	if (fhd1 != fhd2) {
		return fhd2 - fhd1;
	}

	/* Prefer H.264/VC1 over MPEG1/2 */
	return mp12_2 - mp12_1;
}

static int _pl_guess_main_title(MPLS_PL *p1, MPLS_PL *p2)
{
	uint32_t d1 = _pl_duration(p1);
	uint32_t d2 = _pl_duration(p2);

	/* If both longer than 30 min */
	if (d1 > 30*60*45000 && d2 > 30*60*45000) {
		/* Prefer many chapters over few chapters */
		int chap_diff = _pl_chapter_count(p2) - _pl_chapter_count(p1);
		if (chap_diff < -3 || chap_diff > 3) {
			/* Chapter count differs by more than 3 */
			return chap_diff;
		}
		/* Check video: prefer HD over SD, H.264/VC1 over MPEG1/2 */
		int vid_diff = _cmp_video_props(p1, p2);
		if (vid_diff) {
			return vid_diff;
		}
	}

	/* Compare playlist duration, select longer playlist */
	if (d1 < d2) {
		return 1;
	}
	if (d1 > d2) {
		return -1;
	}

	return 0;
}

static int storeInfo(MPLS_PL *pl, titlelist *tList, int pos)
{
	int ii;

	tList[pos].duration = _pl_duration(pl);
	for (ii = 0; ii < pl->list_count; ii++) {
		MPLS_PI *pi = &pl->play_item[ii];
		strcpy(tList[pos].clip_id, pi->clip[0].clip_id);
		//printf("%s.m2ts ", pi->clip[0].clip_id);
	}

	return 0;
}

static int parseInfo(const char *bd_path, titlelist *tList)
{
	//printf("Directory: %s:\n", bd_path);
	MPLS_PL *pl;
	int ii, ti = 1, pl_ii = 0, main_ii = 0;
	MPLS_PL *pl_list[1000];
	struct stat st;
	char *path = NULL;
	DIR *dir = NULL;

	/* Open playlist directory */
	path = _mk_path(bd_path, "/BDMV/PLAYLIST");
	if (path == NULL) {
		fprintf(stderr, "[blurayinfo] Failed to find playlist path: %s\n", bd_path);
		return 0;
	}
	dir = opendir(path);
	if (dir == NULL) {
		fprintf(stderr, "[blurayinfo] Failed to open dir: %s\n", path);
		free(path);
		return 0;
	}

	/* Open and sort playlists */
	char **dirlist = (char**)calloc(10001, sizeof(char*));
	struct dirent *ent;
	int jj = 0;
	for (ent = readdir(dir); ent != NULL; ent = readdir(dir)) {
		dirlist[jj++] = strcpy((char*)malloc(strlen(ent->d_name)), ent->d_name);
	}
	qsort(dirlist, jj, sizeof(char*), _qsort_str_cmp);

	/* Parse playlists */
	for (jj = 0; dirlist[jj] != NULL; jj++) {
		char *name = NULL;
		name = _mk_path(path, dirlist[jj]);
		free(dirlist[jj]);
		if (stat(name, &st)) {
			free(name);
			continue;
		}
		if (!S_ISREG(st.st_mode)) {
			free(name);
			continue;
		}
		/* Filter out short and duplicate playlists */
		pl = _process_file(name, pl_list, pl_ii);
		free(name);
		if (pl != NULL) {
			pl_list[pl_ii] = pl;
			/* Main title guessing */
			if (pl_ii > 0 && _pl_guess_main_title(pl_list[pl_ii], pl_list[main_ii]) <= 0) {
				main_ii = pl_ii;
			}
			pl_ii++;
		}
	}
	free(dirlist);
	free(path);
	closedir(dir);
	dir = NULL;

	/* Store and clean usable playlists */
	for (ii = 0; ii < pl_ii; ii++) {
		if (ii == main_ii) {
			//printf("Main: ");
			storeInfo(pl_list[ii], tList, 0);
		}
		else {
			storeInfo(pl_list[ii], tList, ti++);
		}
		//printf("%d -- Duration: %4u:%02u\n", ii, _pl_duration(pl_list[ii]) / (45000 * 60), (_pl_duration(pl_list[ii]) / 45000) % 60);
		bd_free_mpls(pl_list[ii]);
	}

	return 1;
}

titlelist *newTitleList(void)
{
	titlelist *tList = malloc(sizeof(titlelist)*40);
	if(!tList) {
		exit(0);
	}
	memset(tList, 0, sizeof(titlelist)*40);
	return tList;
}

void freeTitleList(titlelist *tList)
{
	free(tList);
}

PyObject *_getTitles(PyObject *self, PyObject *args)
{
	titlelist *tList;
	int i;
	char *s;
	PyObject *plist, *result, *duration, *clip_id;

	if(!PyArg_ParseTuple(args, "s", &s)) {
		fprintf(stderr, "[blurayinfo] getTitles: wrong arguments!\n");
		return NULL;
	}

	if(!(plist = PyList_New(0))) {
		return NULL;
	}
	if(!(result = PyList_New(0))) {
		return NULL;
	}

	tList = newTitleList();
	if(!parseInfo(s, tList)) {
		fprintf(stderr, "[blurayinfo] getTitles: error in parse!\n");
		return NULL;
	}

	for (i=0; i<1000; i++) {
		if(tList[i].clip_id[0] == '\0') {
			break;
		}
		else {
			duration = Py_BuildValue("k", (unsigned long)tList[i].duration);
			clip_id = Py_BuildValue("s", tList[i].clip_id);
			PyList_Append(plist, duration);
			PyList_Append(plist, clip_id);
			PyList_Append(result, plist);
			if(!(plist = PyList_New(0))) {
				freeTitleList(tList);
				return NULL;
			}
		}
	}

	freeTitleList(tList);
	return result;
}

static PyMethodDef blurayinfo_funcs[] = {
	{"getTitles", _getTitles, METH_VARARGS},
	{NULL, NULL}
};

void initblurayinfo(void)
{
	Py_InitModule("blurayinfo", blurayinfo_funcs);
}

